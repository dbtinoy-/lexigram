"""AUDIT_DEPENDENCIES.md generator: uv freshness plus workspace manifest evidence."""

from __future__ import annotations

from pathlib import Path
import re

from scripts.audit.generators.base import MarkdownAuditGenerator
from scripts.check_dep_pins import iter_member_pyprojects, scan_unbounded_pins
from scripts.core.command_runner import run_command

FRESHNESS_COMMAND = ("uv", "pip", "list", "--outdated")
FRESHNESS_TIMEOUT_SECONDS = 180.0


def _parse_outdated_rows(stdout: str) -> list[tuple[str, str, str, str]]:
    """Parse ``uv pip list --outdated`` output into package rows."""

    rows: list[tuple[str, str, str, str]] = []
    separator = re.compile(r"^[- ]+$")
    for line in stdout.splitlines():
        if not line.strip():
            continue
        if separator.match(line):
            continue
        if line.startswith("Package"):
            continue
        tokens = line.split()
        if len(tokens) < 3:
            continue
        package, version, latest = tokens[:3]
        package_type = " ".join(tokens[3:]) if len(tokens) > 3 else ""
        rows.append((package, version, latest, package_type))
    return rows


class DependenciesAuditGenerator(MarkdownAuditGenerator):
    """Generate AUDIT_DEPENDENCIES.md from freshness and manifest evidence."""

    name = "dependencies"
    description = (
        "Generate AUDIT_DEPENDENCIES.md from uv pip freshness "
        "and workspace manifest scans."
    )
    output_file = "AUDIT_DEPENDENCIES.md"

    def render_markdown(self, *, root: Path) -> str:
        """Render the dependency freshness audit report."""

        freshness = run_command(
            FRESHNESS_COMMAND,
            cwd=root,
            timeout=FRESHNESS_TIMEOUT_SECONDS,
        )
        outdated_rows = (
            _parse_outdated_rows(freshness.stdout) if freshness.exit_code == 0 else []
        )
        freshness_ok = freshness.exit_code == 0 and freshness.timed_out is False

        pin_guard = run_command(
            ("uv", "run", "python", "scripts/check_dep_pins.py", "--root", str(root)),
            cwd=root,
            timeout=60.0,
        )
        pin_guard_ok = pin_guard.exit_code == 0 and pin_guard.timed_out is False

        pins, _scanned = scan_unbounded_pins(root)
        unbounded_total = sum(len(pairs) for pairs in pins.values())
        member_rows = list(iter_member_pyprojects(root))

        markdown = """# AUDIT_DEPENDENCIES.md — Lexigram Framework Dependency Freshness Snapshot

> **Source**: Live command evidence from `uv pip list --outdated` and workspace
> manifest scans against `scripts/check_dep_pins.py`.

---

## Summary

"""
        markdown += f"- Outdated packages detected: {len(outdated_rows)}\n"
        markdown += f"- Workspace members with own pyproject.toml: {len(member_rows)}\n"
        markdown += f"- Unbounded third-party pins (baseline debt): {unbounded_total}\n"
        if not freshness_ok:
            markdown += "- Freshness scan: FAILED (index unreachable or timeout)\n"
        if not pin_guard_ok:
            markdown += "- Pin guard: FAILED — new unbounded pins detected\n"
        markdown += "\n## Tool Results\n\n"
        markdown += "| Tool | Status | Exit Code | Duration | Command |\n"
        markdown += "|------|--------|-----------|----------|---------|\n"
        markdown += (
            f"| `uv pip list --outdated` | **{'PASS' if freshness_ok else 'FAIL'}** | "
            f"{freshness.exit_code if freshness.exit_code is not None else 'timeout'} | "
            f"{freshness.duration_ms} ms | `uv pip list --outdated` |\n"
        )
        markdown += (
            f"| `check_dep_pins.py` | **{'PASS' if pin_guard_ok else 'FAIL'}** | "
            f"{pin_guard.exit_code if pin_guard.exit_code is not None else 'timeout'} | "
            f"{pin_guard.duration_ms} ms | `uv run python scripts/check_dep_pins.py` |\n"
        )
        markdown += "\n"

        markdown += "## Outdated Packages\n\n"
        if not outdated_rows:
            markdown += "No outdated packages detected.\n"
        else:
            markdown += "| Package | Installed | Latest | Type |\n"
            markdown += "|---------|-----------|--------|------|\n"
            for package, version, latest, package_type in outdated_rows:
                type_label = (
                    "workspace (editable)"
                    if package_type.startswith("/")
                    else (package_type or "wheel")
                )
                markdown += f"| `{package}` | {version} | {latest} | {type_label} |\n"
        markdown += "\n## Direct Dependency Manifest\n\n"
        markdown += "| Member | Own pyproject | Unbounded third-party pins |\n"
        markdown += "|--------|---------------|----------------------------|\n"
        for name, _path, _data in member_rows:
            pin_count = len(pins.get(name, []))
            markdown += f"| `{name}` | yes | {pin_count} |\n"
        markdown += (
            "\nBaseline guard: `scripts/check_dep_pins.py` fails CI on unbounded "
            "third-party pins not covered by `scripts/dep_pins_baseline.json`; "
            "regenerate deliberately with `--write-baseline`.\n"
        )
        return markdown
