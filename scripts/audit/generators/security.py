from __future__ import annotations

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
RUFF_CRITICAL_CODES = frozenset(
    {"S301", "S307", "S501", "S506", "S603", "S607", "S608", "S701"}
)
RUFF_NOISE_CODES = frozenset({"S101", "S105", "S106"})
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
        rule_result = run_rules(root)
        sec_findings = tuple(
            finding for finding in rule_result.findings if finding.rule_id.startswith("sec-")
        )
        tracker_path = root / "docs" / "AUDIT_TRACKER.md"
        tracker_text = tracker_path.read_text(encoding="utf-8") if tracker_path.is_file() else ""
        rows = parse_tracker_rows(tracker_text) if tracker_text else ()
        verdict, verdict_reason = _compute_verdict(rows, sec_findings, ruff_findings)

        markdown = """# AUDIT_SECURITY.md — Lexigram Framework Security Audit

> **Source**: Live command evidence (pip-audit, ruff bandit rules), framework security rules, and the audit tracker (`docs/AUDIT_TRACKER.md`).

---

## Summary

"""
        markdown += f"- Verdict: **{verdict}** — {verdict_reason}\n"
        markdown += f"- Dependency scan: {_status_word(pip_evidence['exit_code'])}\n"
        markdown += (
            f"- SAST (ruff `S` rules): {len(ruff_findings)} finding(s) "
            f"({_finding_count(ruff_findings)} high-signal)\n"
        )
        markdown += f"- Framework security rules: {len(sec_findings)} finding(s)\n"
        markdown += f"- Tracker areas: {len(rows)} total, {sum(1 for row in rows if row_is_done(row))} done\n\n"
        markdown += _render_dependency_section(pip_evidence)
        markdown += _render_ruff_section(ruff_findings, ruff_evidence)
        markdown += _render_rules_section(sec_findings)
        markdown += _render_tracker_section(rows)
        markdown += _render_verified_clean_section(tracker_text)
        markdown += _render_open_risk_table(rows)
        return markdown


def _run_pip_audit(*, root: Path) -> dict[str, str | int | bool | None]:
    """Run pip-audit with a uv fallback and return normalized evidence."""

    primary = run_command(("uv", "run", "pip-audit"), cwd=root, timeout=PIP_AUDIT_TIMEOUT)
    output = primary.stdout + primary.stderr
    if primary.exit_code not in (None, 0) and re.search(
        r"no module|no such file|command not found|unrecognized subcommand|not found",
        output,
        re.IGNORECASE,
    ):
        fallback = run_command(("uv", "pip", "audit"), cwd=root, timeout=PIP_AUDIT_TIMEOUT)
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


def _compute_verdict(
    rows: tuple[TrackerRow, ...],
    sec_findings: tuple[RuleFinding, ...],
    ruff_findings: set[tuple[str, int, str, str]],
) -> tuple[str, str]:
    """Compute the report verdict and a one-line justification."""

    if any(finding.severity is RuleSeverity.CRITICAL for finding in sec_findings):
        return "CRITICAL", "a critical framework security rule fired"
    if any(finding[2] in RUFF_CRITICAL_CODES for finding in ruff_findings):
        return "CRITICAL", "a critical bandit rule fired"
    if any("critical" in row.severity_mix.lower() for row in rows if not row_is_done(row)):
        return "CRITICAL", "open audit-tracker areas with Critical findings"
    if sec_findings or ruff_findings:
        return "WARN", "static analysis found issues to review"
    if any("high" in row.severity_mix.lower() for row in rows if not row_is_done(row)):
        return "WARN", "open audit-tracker areas with High findings"
    return "PASS", "no open critical, high, or static-analysis findings"


def _render_dependency_section(evidence: dict[str, str | int | bool | None]) -> str:
    """Render the pip-audit evidence section."""

    output = str(evidence["stdout"]) + str(evidence["stderr"])
    summary = output.strip().splitlines()[-1] if output.strip() else "(no output)"
    markdown = "## Dependency Scan\n\n"
    markdown += f"- Command: `{evidence['command']}`\n"
    markdown += f"- Exit code: `{evidence['exit_code']}`\n"
    markdown += f"- Duration: `{evidence['duration_ms']} ms`\n"
    markdown += f"- Summary: `{summary}`\n\n"
    markdown += "```text\n"
    markdown += f"{output.strip()[:1500]}\n"
    markdown += "```\n\n"
    return markdown


def _render_ruff_section(
    findings: set[tuple[str, int, str, str]],
    evidence: CommandEvidence,
) -> str:
    """Render the ruff bandit SAST section, separating noise rules."""

    markdown = "## Static Analysis (ruff bandit rules)\n\n"
    markdown += f"- Exit code: `{evidence.exit_code}`\n\n"
    real = sorted(finding for finding in findings if finding[2] not in RUFF_NOISE_CODES)
    noise = sorted(finding for finding in findings if finding[2] in RUFF_NOISE_CODES)
    markdown += "### Findings\n\n"
    markdown += "| File | Line | Rule | Message |\n"
    markdown += "|------|------|------|---------|\n"
    if real:
        for path, line, code, message in real:
            markdown += f"| `{path}` | {line} | `{code}` | {_escape_cell(message)} |\n"
    else:
        markdown += "| `(none)` | 0 | `-` | No high-signal bandit findings. |\n"
    markdown += "\n### Low-Signal Rules (S101 asserts, S105/S106 hardcoded strings)\n\n"
    markdown += f"- Count: {len(noise)}\n\n"
    if noise:
        markdown += "| File | Line | Rule | Message |\n"
        markdown += "|------|------|------|---------|\n"
        for path, line, code, message in noise:
            markdown += f"| `{path}` | {line} | `{code}` | {_escape_cell(message)} |\n"
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
    return "failed"


def _escape_cell(value: str) -> str:
    """Escape markdown table control characters inside cell content."""

    return value.replace("|", "\\|").replace("\n", " ")
