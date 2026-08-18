from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from lexigram.serialization.backends import json as json_backend
from dev.audit.generators.base import AuditGeneratorProtocol
from dev.core.registry import GeneratorRegistry
from dev.core.validation import (
    RulesReportSummary,
    ToolHealthResult,
    parse_quality_tool_health,
    parse_rules_report_summary,
    parse_tests_tool_health,
)

STATUS_BUCKETS = ("correct", "incomplete", "suspect")


@dataclass(frozen=True, slots=True)
class AuditIndexEntry:
    """Summary row for one registered audit report."""

    name: str
    description: str
    report_path: str
    json_path: str
    total_rows: int
    correct: int
    incomplete: int
    suspect: int
    available: bool

    def as_dict(self) -> dict[str, object]:
        """Convert the entry to a JSON-serializable mapping."""

        return {
            "name": self.name,
            "description": self.description,
            "report_path": self.report_path,
            "json_path": self.json_path,
            "total_rows": self.total_rows,
            "status_buckets": {
                "correct": self.correct,
                "incomplete": self.incomplete,
                "suspect": self.suspect,
            },
            "available": self.available,
        }


@dataclass(frozen=True, slots=True)
class AuditIndexSnapshot:
    """Structured summary for the audit index output."""

    generated_at: str
    entries: tuple[AuditIndexEntry, ...]
    total_rows: int
    correct: int
    incomplete: int
    suspect: int
    tool_health: tuple[ToolHealthResult, ...]
    rules_summary: RulesReportSummary
    missing_packages: tuple[str, ...]

    def as_dict(
        self,
        *,
        output_markdown: str,
        output_json: str,
    ) -> dict[str, object]:
        """Convert the snapshot to a JSON-serializable mapping."""

        return {
            "generated_at": self.generated_at,
            "output_markdown": output_markdown,
            "output_json": output_json,
            "registered_audits": len(self.entries),
            "reports_present": sum(1 for entry in self.entries if entry.available),
            "total_rows": self.total_rows,
            "status_buckets": {
                "correct": self.correct,
                "incomplete": self.incomplete,
                "suspect": self.suspect,
            },
            "tool_health": {
                tool_result.tool: {
                    "status": tool_result.status,
                    "source_audit": tool_result.source_audit,
                }
                for tool_result in self.tool_health
            },
            "rules_summary": {
                "critical": self.rules_summary.critical,
                "important": self.rules_summary.important,
                "minor": self.rules_summary.minor,
                "top_misalignments": [
                    {
                        "rule_id": finding.rule_id,
                        "count": finding.count,
                    }
                    for finding in self.rules_summary.top_misalignments
                ],
            },
            "package_coverage": {
                "discovered_packages": self.rules_summary.discovered_packages,
                "covered_packages": self.rules_summary.covered_packages,
                "missing_packages": list(self.missing_packages),
                "coverage_status": self.rules_summary.coverage_status,
            },
            "reports": [entry.as_dict() for entry in self.entries],
        }


def build_audit_index(
    root: Path,
    registry: GeneratorRegistry[AuditGeneratorProtocol],
    *,
    self_name: str | None = None,
    report_dir: Path | None = None,
) -> AuditIndexSnapshot:
    """Collect summary data for all registered audit generators."""

    generated_at = datetime.now(tz=UTC).isoformat()
    summaries = tuple(
        _summarize_generator(root=root, generator=generator, self_name=self_name, report_dir=report_dir)
        for name in registry.names()
        if (generator := registry.get(name)) is not None
    )
    entries = tuple(summary.entry for summary in summaries)
    tool_health = _collect_tool_health(summaries)
    rules_summary = _collect_rules_summary(summaries)
    return AuditIndexSnapshot(
        generated_at=generated_at,
        entries=entries,
        total_rows=sum(entry.total_rows for entry in entries),
        correct=sum(entry.correct for entry in entries),
        incomplete=sum(entry.incomplete for entry in entries),
        suspect=sum(entry.suspect for entry in entries),
        tool_health=tool_health,
        rules_summary=rules_summary,
        missing_packages=rules_summary.missing_packages,
    )


def render_index_markdown(
    snapshot: AuditIndexSnapshot,
    *,
    output_markdown: str,
    output_json: str,
) -> str:
    """Render the audit index as markdown."""

    markdown = f"""# {output_markdown} — Lexigram Framework Audit Index

> **Source**: Registered audit generators and derived report summaries.
> **Generated JSON**: `{output_json}`
> **Status buckets**: `correct`, `incomplete`, `suspect` default to `0` when a report does not expose them.

---

## Summary

"""
    markdown += f"- Registered audits: {len(snapshot.entries)}\n"
    markdown += f"- Reports present: {sum(1 for entry in snapshot.entries if entry.available)}\n"
    markdown += f"- Total rows/findings: {snapshot.total_rows}\n"
    markdown += f"- `correct`: {snapshot.correct}\n"
    markdown += f"- `incomplete`: {snapshot.incomplete}\n"
    markdown += f"- `suspect`: {snapshot.suspect}\n\n"
    markdown += "## Tool Health\n\n"
    markdown += "| Tool | Status | Source |\n"
    markdown += "|------|--------|--------|\n"
    if snapshot.tool_health:
        for tool_result in snapshot.tool_health:
            markdown += (
                f"| `{tool_result.tool}` | {tool_result.status} | "
                f"`{tool_result.source_audit}` |\n"
            )
    else:
        markdown += "| `(none)` | UNKNOWN | `n/a` |\n"
    markdown += "\n"
    markdown += "## Rules Health\n\n"
    markdown += f"- Critical violations: {snapshot.rules_summary.critical}\n"
    markdown += f"- Important violations: {snapshot.rules_summary.important}\n"
    markdown += f"- Minor violations: {snapshot.rules_summary.minor}\n"
    markdown += "- Top misalignments:\n"
    if snapshot.rules_summary.top_misalignments:
        for misalignment in snapshot.rules_summary.top_misalignments:
            markdown += f"  - `{misalignment.rule_id}`: {misalignment.count}\n"
    else:
        markdown += "  - `(none)`\n"
    markdown += "\n"
    markdown += "## Package Coverage\n\n"
    markdown += (
        f"- Discovered packages: {snapshot.rules_summary.discovered_packages or 0}\n"
    )
    markdown += f"- Covered packages: {snapshot.rules_summary.covered_packages or 0}\n"
    markdown += f"- Missing packages: {len(snapshot.missing_packages)}\n"
    coverage_status = snapshot.rules_summary.coverage_status
    markdown += (
        f"- Coverage status: {'PASS' if coverage_status else 'FAIL'}\n"
        if coverage_status is not None
        else "- Coverage status: UNKNOWN\n"
    )
    markdown += "- Missing package list:\n"
    if snapshot.missing_packages:
        for package_name in snapshot.missing_packages:
            markdown += f"  - `{package_name}`\n"
    else:
        markdown += "  - `(none)`\n"
    markdown += "\n"
    markdown += "## Registered Reports\n\n"
    markdown += (
        "| Audit | Report Path | Rows | correct | incomplete | suspect | Status |\n"
    )
    markdown += (
        "|-------|-------------|-----:|--------:|-----------:|--------:|--------|\n"
    )
    for entry in snapshot.entries:
        status = "present" if entry.available else "missing"
        markdown += (
            f"| `{entry.name}` | `{entry.report_path}` | {entry.total_rows} | "
            f"{entry.correct} | {entry.incomplete} | {entry.suspect} | {status} |\n"
        )
    markdown += "\n"
    return markdown


def render_index_json(
    snapshot: AuditIndexSnapshot,
    *,
    output_markdown: str,
    output_json: str,
) -> str:
    """Render the audit index as JSON."""

    return json_backend.dumps_str(
        snapshot.as_dict(
            output_markdown=output_markdown,
            output_json=output_json,
        ),
        indent=2,
        sort_keys=True,
    ) + "\n"


def _summarize_generator(
    *,
    root: Path,
    generator: AuditGeneratorProtocol,
    self_name: str | None,
    report_dir: Path | None = None,
) -> _GeneratorSummary:
    """Summarize one registered generator report."""

    report_path = generator.output_file
    json_path = Path(report_path).with_suffix(".json").name
    source_path = (report_dir if report_dir is not None else root) / report_path

    if self_name is not None and generator.name == self_name:
        return _GeneratorSummary(
            entry=AuditIndexEntry(
                name=generator.name,
                description=generator.description,
                report_path=report_path,
                json_path=json_path,
                total_rows=0,
                correct=0,
                incomplete=0,
                suspect=0,
                available=True,
            ),
            report_text=None,
        )

    if not source_path.is_file():
        return _GeneratorSummary(
            entry=AuditIndexEntry(
                name=generator.name,
                description=generator.description,
                report_path=report_path,
                json_path=json_path,
                total_rows=0,
                correct=0,
                incomplete=0,
                suspect=0,
                available=False,
            ),
            report_text=None,
        )

    report_text = source_path.read_text(encoding="utf-8")
    total_rows, status_buckets = _summarize_report_text(report_text)
    return _GeneratorSummary(
        entry=AuditIndexEntry(
            name=generator.name,
            description=generator.description,
            report_path=report_path,
            json_path=json_path,
            total_rows=total_rows,
            correct=status_buckets["correct"],
            incomplete=status_buckets["incomplete"],
            suspect=status_buckets["suspect"],
            available=True,
        ),
        report_text=report_text,
    )


def _summarize_report_text(report_text: str) -> tuple[int, dict[str, int]]:
    """Count table rows and status values from markdown content."""

    total_rows = 0
    status_buckets = dict.fromkeys(STATUS_BUCKETS, 0)
    for row in _iter_markdown_rows(report_text):
        total_rows += 1
        cells = [cell.strip().lower() for cell in row.strip("|").split("|")]
        for cell in cells:
            if cell in status_buckets:
                status_buckets[cell] += 1
    return total_rows, status_buckets


def _iter_markdown_rows(report_text: str) -> tuple[str, ...]:
    """Yield data rows from markdown tables."""

    rows: list[str] = []
    table_lines: list[str] = []
    for line in report_text.splitlines():
        if line.lstrip().startswith("|"):
            table_lines.append(line.rstrip())
            continue
        rows.extend(_table_data_rows(table_lines))
        table_lines = []
    rows.extend(_table_data_rows(table_lines))
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class _GeneratorSummary:
    """Internal report summary carrying both entry and source text."""

    entry: AuditIndexEntry
    report_text: str | None


def _collect_tool_health(
    summaries: tuple[_GeneratorSummary, ...],
) -> tuple[ToolHealthResult, ...]:
    """Collect normalized tool health across supported audit reports."""

    aggregated: dict[str, ToolHealthResult] = {}
    for summary in summaries:
        report_text = summary.report_text
        if report_text is None:
            continue
        if summary.entry.name == "quality":
            for tool_result in parse_quality_tool_health(report_text):
                aggregated[tool_result.tool] = tool_result
        if summary.entry.name == "tests":
            for tool_result in parse_tests_tool_health(report_text):
                existing = aggregated.get(tool_result.tool)
                if existing is None or existing.status != "FAIL":
                    aggregated[tool_result.tool] = tool_result
    return tuple(aggregated[name] for name in sorted(aggregated))


def _collect_rules_summary(summaries: tuple[_GeneratorSummary, ...]) -> RulesReportSummary:
    """Return parsed rules summary data when the rules report is available."""

    for summary in summaries:
        if summary.entry.name != "rules" or summary.report_text is None:
            continue
        return parse_rules_report_summary(summary.report_text)
    return RulesReportSummary(
        critical=0,
        important=0,
        minor=0,
        top_misalignments=(),
        discovered_packages=None,
        covered_packages=None,
        missing_packages=(),
        coverage_status=None,
    )


def _table_data_rows(table_lines: list[str]) -> list[str]:
    """Extract data rows from a contiguous markdown table block."""

    if not table_lines:
        return []
    if len(table_lines) == 1:
        return []
    data_start = 1 if _is_table_separator(table_lines[1]) else 0
    data_rows = table_lines[data_start + 1 :] if data_start == 1 else table_lines[1:]
    return [row for row in data_rows if not _is_table_separator(row)]


def _is_table_separator(row: str) -> bool:
    """Return True when a markdown row is a separator line."""

    cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
    if not cells:
        return False
    return all(_is_separator_cell(cell) for cell in cells)


def _is_separator_cell(cell: str) -> bool:
    """Return True when a markdown table cell is a separator segment."""

    if len(cell.replace(":", "").replace("-", "")) != 0:
        return False
    stripped = cell.replace(":", "")
    return stripped.count("-") >= 3
