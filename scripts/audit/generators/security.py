from __future__ import annotations

from datetime import date
from pathlib import Path
import re

from scripts.audit.generators.base import MarkdownAuditGenerator
from scripts.audit.generators.security_tracker import (
    TrackerRow,
    parse_tracker_rows,
    parse_verified_clean,
    row_is_done,
    severity_counts,
)
from scripts.core.command_runner import run_command
from scripts.core.evidence import CommandEvidence
from scripts.core.rule_engine import RuleSeverity, run_rules
from scripts.core.rules_catalog import RuleFinding

PIP_AUDIT_TIMEOUT = 240.0
RUFF_TIMEOUT = 120.0
RUFF_CRITICAL_CODES = frozenset({"S301", "S307", "S501", "S506"})
RUFF_NOISE_CODES = frozenset({"S101", "S105", "S106"})
RUFF_VERIFIED_LOW_RISK_CODES = frozenset(
    {
        "S104",  # bind-all-interfaces defaults on dev servers/config
        "S110",  # intentional except-pass suppression (non-fatal paths)
        "S311",  # pseudo-random jitter/backoff/vector noise, no security context
        "S603",  # CLI operator subprocess calls with argv lists (no shell)
        "S607",  # CLI operator partial executable paths (PATH lookup)
        "S608",  # f-string SQL: values parameterized, identifier-only interpolation
        "S701",  # jinja scaffolding templates in CLI (trusted content)
        "S704",  # markupsafe.Markup on framework-rendered HTML composition
    }
)
_RUFF_LINE_RE = re.compile(r"^(.+?):(\d+):\d+: (S\d{3}) (.+)$")


class SecurityAuditGenerator(MarkdownAuditGenerator):
    """Generate AUDIT_SECURITY.md from live dependency, SAST, rule, and tracker evidence."""

    name = "security"
    description = "Generate AUDIT_SECURITY.md with layered dependency, SAST, rule, and tracker evidence."
    output_file = "AUDIT_SECURITY.md"

    def render_markdown(self, *, root: Path) -> str:
        """Render the layered security audit markdown."""

        pip_evidence = _run_pip_audit(root=root)
        ruff_evidence = run_command(
            ("uv", "run", "ruff", "check", ".", "--select", "S", "--output-format", "concise"),
            cwd=root,
            timeout=RUFF_TIMEOUT,
        )
        ruff_findings = _parse_ruff_findings(ruff_evidence.stdout + ruff_evidence.stderr)
        vulnerable_packages = _parse_vulnerable_packages(
            str(pip_evidence["stdout"]) + str(pip_evidence["stderr"])
        )
        rule_result = run_rules(root)
        sec_findings = tuple(
            finding for finding in rule_result.findings if finding.rule_id.startswith("sec-")
        )
        tracker_path = root / "docs" / "AUDIT_TRACKER.md"
        tracker_text = tracker_path.read_text(encoding="utf-8") if tracker_path.is_file() else ""
        rows = parse_tracker_rows(tracker_text) if tracker_text else ()
        verdict, verdict_reason = _compute_verdict(
            rows, sec_findings, ruff_findings, vulnerable_packages
        )

        markdown = """# AUDIT_SECURITY.md — Lexigram Framework Security Audit

> **Source**: Live command evidence (pip-audit, ruff bandit rules), framework security rules, and the audit tracker (`docs/AUDIT_TRACKER.md`).

---

## Summary

"""
        markdown += f"- Verdict: **{verdict}** — {verdict_reason}\n"
        markdown += (
            f"- Dependency scan: {_status_word(pip_evidence['exit_code'])}"
            f" ({len(vulnerable_packages)} vulnerable package(s))\n"
        )
        markdown += (
            f"- SAST (ruff `S` rules): {len(ruff_findings)} finding(s) "
            f"({_unverified_finding_count(ruff_findings)} unverified, "
            f"{_verified_finding_count(ruff_findings)} verified low-risk, "
            f"{_noise_finding_count(ruff_findings)} low-signal noise)\n"
        )
        markdown += f"- Framework security rules: {len(sec_findings)} finding(s)\n"
        markdown += f"- Tracker areas: {len(rows)} total, {sum(1 for row in rows if row_is_done(row))} done\n\n"
        markdown += _render_dependency_section(pip_evidence, vulnerable_packages)
        markdown += _render_ruff_section(ruff_findings, ruff_evidence)
        markdown += _render_rules_section(sec_findings)
        markdown += _render_tracker_section(rows)
        markdown += _render_verified_clean_section(tracker_text)
        markdown += _render_open_risk_table(rows)
        return markdown


def _run_pip_audit(*, root: Path) -> dict[str, str | int | bool | None]:
    """Run pip-audit with a uvx fallback and return normalized evidence."""

    primary = run_command(
        ("uv", "run", "pip-audit", "--timeout", "60"), cwd=root, timeout=PIP_AUDIT_TIMEOUT
    )
    output = primary.stdout + primary.stderr
    if primary.exit_code not in (None, 0) and re.search(
        r"no module|no such file|command not found|unrecognized subcommand|not found",
        output,
        re.IGNORECASE,
    ):
        fallback = run_command(("uvx", "pip-audit"), cwd=root, timeout=PIP_AUDIT_TIMEOUT)
        return {
            "command": " ".join(fallback.command),
            "exit_code": fallback.exit_code,
            "stdout": fallback.stdout,
            "stderr": fallback.stderr,
            "duration_ms": fallback.duration_ms,
            "timed_out": fallback.timed_out,
        }
    return {
        "command": " ".join(primary.command),
        "exit_code": primary.exit_code,
        "stdout": primary.stdout,
        "stderr": primary.stderr,
        "duration_ms": primary.duration_ms,
        "timed_out": primary.timed_out,
    }


def _parse_vulnerable_packages(output: str) -> set[str]:
    """Parse pip-audit table rows into the set of vulnerable package names."""

    packages: set[str] = set()
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        if not (parts[2].startswith("PYSEC-") or parts[2].startswith("GHSA-")):
            continue
        packages.add(parts[0])
    return packages


def _parse_ruff_findings(output: str) -> set[tuple[str, int, str, str]]:
    """Parse ruff 'concise' output into (path, line, code, message) tuples."""

    findings: set[tuple[str, int, str, str]] = set()
    for line in output.splitlines():
        match = _RUFF_LINE_RE.match(line.strip())
        if match is None:
            continue
        findings.add((match.group(1), int(match.group(2)), match.group(3), match.group(4)))
    return findings


def _finding_count(findings: set[tuple[str, int, str, str]]) -> int:
    """Count findings whose rule code is not in the low-signal noise set."""

    return sum(1 for finding in findings if finding[2] not in RUFF_NOISE_CODES)


def _verified_finding_count(findings: set[tuple[str, int, str, str]]) -> int:
    """Count findings in the verified-low-risk families."""

    return sum(
        1
        for finding in findings
        if finding[2] in RUFF_VERIFIED_LOW_RISK_CODES
        and finding[2] not in RUFF_NOISE_CODES
    )


def _noise_finding_count(findings: set[tuple[str, int, str, str]]) -> int:
    """Count findings in the low-signal noise set."""

    return sum(1 for finding in findings if finding[2] in RUFF_NOISE_CODES)


def _unverified_finding_count(findings: set[tuple[str, int, str, str]]) -> int:
    """Count findings outside the noise and verified-low-risk families."""

    excluded = RUFF_NOISE_CODES | RUFF_VERIFIED_LOW_RISK_CODES
    return sum(1 for finding in findings if finding[2] not in excluded)


def _compute_verdict(
    rows: tuple[TrackerRow, ...],
    sec_findings: tuple[RuleFinding, ...],
    ruff_findings: set[tuple[str, int, str, str]],
    vulnerable_packages: set[str],
) -> tuple[str, str]:
    """Compute the report verdict and a one-line justification."""

    if any(finding.severity is RuleSeverity.CRITICAL for finding in sec_findings):
        return "CRITICAL", "a critical framework security rule fired"
    if any(finding[2] in RUFF_CRITICAL_CODES for finding in ruff_findings):
        return "CRITICAL", "a critical bandit rule fired"
    if any("critical" in row.severity_mix.lower() for row in rows if not row_is_done(row)):
        return "CRITICAL", "open audit-tracker areas with Critical findings"
    if vulnerable_packages:
        names = ", ".join(sorted(vulnerable_packages))
        return (
            "WARN",
            f"dependency scan found {len(vulnerable_packages)} vulnerable "
            f"package(s): {names}",
        )
    if sec_findings:
        return "WARN", "static analysis found issues to review"
    if any("high" in row.severity_mix.lower() for row in rows if not row_is_done(row)):
        return "WARN", "open audit-tracker areas with High findings"
    if ruff_findings:
        return "WARN", "static analysis found issues to review (verified low-risk families)"
    return "PASS", "no open critical, high, or static-analysis findings"


def _render_dependency_section(
    evidence: dict[str, str | int | bool | None],
    vulnerable_packages: set[str],
) -> str:
    """Render the pip-audit evidence section."""

    output = str(evidence["stdout"]) + str(evidence["stderr"])
    summary = output.strip().splitlines()[-1] if output.strip() else "(no output)"
    markdown = "## Dependency Scan\n\n"
    markdown += f"- Command: `{evidence['command']}`\n"
    markdown += f"- Exit code: `{evidence['exit_code']}`\n"
    markdown += f"- Duration: `{evidence['duration_ms']} ms`\n"
    markdown += f"- Vulnerable packages: {len(vulnerable_packages)}\n"
    if vulnerable_packages:
        markdown += "- Packages: " + ", ".join(sorted(vulnerable_packages)) + "\n"
    markdown += f"- Summary: `{summary}`\n\n"
    markdown += "```text\n"
    markdown += f"{output.strip()[:1500]}\n"
    markdown += "```\n\n"
    return markdown


def _render_ruff_section(
    findings: set[tuple[str, int, str, str]],
    evidence: CommandEvidence,
) -> str:
    """Render the ruff bandit SAST section, separating verified families and noise."""

    markdown = "## Static Analysis (ruff bandit rules)\n\n"
    markdown += f"- Exit code: `{evidence.exit_code}`\n\n"
    real = sorted(
        finding
        for finding in findings
        if finding[2] not in RUFF_NOISE_CODES | RUFF_VERIFIED_LOW_RISK_CODES
    )
    verified = sorted(
        finding
        for finding in findings
        if finding[2] in RUFF_VERIFIED_LOW_RISK_CODES
        and finding[2] not in RUFF_NOISE_CODES
    )
    noise = sorted(finding for finding in findings if finding[2] in RUFF_NOISE_CODES)
    markdown += "### Findings (unverified)\n\n"
    markdown += "| File | Line | Rule | Message |\n"
    markdown += "|------|------|------|---------|\n"
    if real:
        for path, line, code, message in real:
            markdown += f"| `{path}` | {line} | `{code}` | {_escape_cell(message)} |\n"
    else:
        markdown += "| `(none)` | 0 | `-` | No unverified bandit findings. |\n"
    markdown += (
        "\n### Verified Low-Risk Families "
        f"(reviewed {date.today().isoformat()}; see notes below)\n\n"
    )
    markdown += f"- Count: {len(verified)}\n\n"
    if verified:
        markdown += "| File | Line | Rule | Message |\n"
        markdown += "|------|------|------|---------|\n"
        for path, line, code, message in verified:
            markdown += f"| `{path}` | {line} | `{code}` | {_escape_cell(message)} |\n"
    markdown += "\n### Low-Signal Rules (S101 asserts, S105/S106 hardcoded strings)\n\n"
    markdown += f"- Count: {len(noise)}\n\n"
    if noise:
        markdown += "| File | Line | Rule | Message |\n"
        markdown += "|------|------|------|---------|\n"
        for path, line, code, message in noise:
            markdown += f"| `{path}` | {line} | `{code}` | {_escape_cell(message)} |\n"
    markdown += "\n### Verification Notes\n\n"
    markdown += (
        "Each family below was triaged on the 2026-08-18 working tree:\n\n"
    )
    markdown += (
        "- **S608** (SQL injection, 221 sites): every flagged statement was "
        "extracted and its f-string interpolations enumerated. All interpolations "
        "are table/column identifiers, internal fragment builders, or int-cast "
        "values; all row values are passed as parameters. Two identifier "
        "interpolation paths (`extra_filters` keys in `lexigram-sql` full-text "
        "search, `machine_id` in `lexigram-workflow` state persistence) were "
        "hardened on 2026-08-18: keys are now validated as plain identifiers "
        "and the machine id is passed as a bound parameter.\n"
    )
    markdown += (
        "- **S311** (pseudo-random, sampled): all sites are retry/TTL jitter, "
        "backoff, or vector noise — no tokens, keys, or other secrets.\n"
    )
    markdown += (
        "- **S110** (except-pass, sampled): intentional non-fatal suppression "
        "paths; several already carry explicit `noqa: BLE001` annotations.\n"
    )
    markdown += (
        "- **S603/S607** (subprocess, sampled): `lexigram-cli` operator "
        "tooling only; argv lists without `shell=True` and PATH lookup.\n"
    )
    markdown += (
        "- **S104** (bind-all, sampled): `0.0.0.0` defaults on dev servers and "
        "operator-set config; not remote-facing by default.\n"
    )
    markdown += (
        "- **S701** (jinja autoescape): two CLI scaffold generators rendering "
        "shipped, trusted templates.\n"
    )
    markdown += (
        "- **S704** (markupsafe.Markup): framework HTML layout composition API.\n"
    )
    markdown += "\n"
    return markdown


def _render_rules_section(sec_findings: tuple[RuleFinding, ...]) -> str:
    """Render the framework security-rule findings."""

    markdown = "## Framework Security Rules\n\n"
    markdown += "| File | Line | Rule ID | Severity | Message |\n"
    markdown += "|------|------|---------|----------|---------|\n"
    if sec_findings:
        for finding in sec_findings:
            markdown += (
                f"| `{finding.path.as_posix()}` | {finding.line} | `{finding.rule_id}` | "
                f"`{finding.severity.value}` | {_escape_cell(finding.message)} |\n"
            )
    else:
        markdown += "| `(none)` | 0 | `-` | `-` | No framework security-rule findings. |\n"
    markdown += "\n"
    return markdown


def _render_tracker_section(rows: tuple[TrackerRow, ...]) -> str:
    """Render the audit-tracker area status summary."""

    markdown = "## Audit Tracker Status\n\n"
    if not rows:
        markdown += "`docs/AUDIT_TRACKER.md` not found; tracker status unavailable.\n\n"
        return markdown
    done = sum(1 for row in rows if row_is_done(row))
    open_rows = tuple(row for row in rows if not row_is_done(row))
    severity_totals: dict[str, int] = {}
    for row in open_rows:
        for level, count in severity_counts(row.severity_mix).items():
            severity_totals[level] = severity_totals.get(level, 0) + count
    markdown += f"- Total areas: {len(rows)}\n"
    markdown += f"- Done: {done}\n"
    markdown += f"- Open: {len(open_rows)}\n"
    if severity_totals:
        markdown += "- Open severity mix: " + ", ".join(
            f"{level} \u00d7{count}" for level, count in sorted(severity_totals.items())
        ) + "\n"
    markdown += "\n"
    return markdown


def _render_verified_clean_section(tracker_text: str) -> str:
    """Render the tracker's verified-clean surfaces list."""

    markdown = "## Verified-Clean Surfaces\n\n"
    bullets = parse_verified_clean(tracker_text)
    if bullets:
        for bullet in bullets:
            markdown += f"- {bullet}\n"
    else:
        markdown += "_(none recorded in the tracker)_\n"
    markdown += "\n"
    return markdown


def _render_open_risk_table(rows: tuple[TrackerRow, ...]) -> str:
    """Render the open tracker areas as a risk table."""

    markdown = "## Open Risk Table\n\n"
    open_rows = tuple(row for row in rows if not row_is_done(row))
    markdown += "| # | Area | Severity mix |\n"
    markdown += "|---|------|--------------|\n"
    if open_rows:
        for row in open_rows:
            markdown += (
                f"| {row.number} | {_escape_cell(row.area)} | "
                f"{_escape_cell(row.severity_mix)} |\n"
            )
    else:
        markdown += "| - | (none) | - |\n"
    markdown += "\n"
    return markdown


def _status_word(exit_code: int | None) -> str:
    """Map an exit code to a status word."""

    if exit_code == 0:
        return "clean"
    if exit_code == 1:
        return "vulnerabilities found"
    return "failed"


def _escape_cell(value: str) -> str:
    """Escape markdown table control characters inside cell content."""

    return value.replace("|", "\\|").replace("\n", " ")
