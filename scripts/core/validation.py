from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
import re


class ReferenceStatus(str, Enum):
    """Status tag for a referenced source."""

    CORRECT = "correct"
    INCOMPLETE = "incomplete"
    SUSPECT = "suspect"


@dataclass(frozen=True, slots=True)
class PackageCoverageResult:
    """Coverage accounting for discovered packages versus covered packages."""

    discovered_packages: frozenset[str]
    covered_packages: frozenset[str]
    missing_packages: frozenset[str]
    success: bool


@dataclass(frozen=True, slots=True)
class ReferenceValidationResult:
    """Validation result for a single referenced source."""

    reference: str
    status: ReferenceStatus
    exists: bool
    complete: bool


@dataclass(frozen=True, slots=True)
class ToolHealthResult:
    """Parsed tool health status for a named tool."""

    tool: str
    status: str
    source_audit: str


@dataclass(frozen=True, slots=True)
class RuleMisalignment:
    """Aggregated count for one recurring rules misalignment."""

    rule_id: str
    count: int


@dataclass(frozen=True, slots=True)
class RulesReportSummary:
    """Parsed rules-report health data used by indexing and validation."""

    critical: int
    important: int
    minor: int
    top_misalignments: tuple[RuleMisalignment, ...]
    discovered_packages: int | None
    covered_packages: int | None
    missing_packages: tuple[str, ...]
    coverage_status: bool | None


def validate_package_coverage(
    discovered: Iterable[str],
    covered: Iterable[str],
) -> PackageCoverageResult:
    """Validate that every discovered package is covered."""

    discovered_packages = frozenset(discovered)
    covered_packages = frozenset(covered)
    missing_packages = discovered_packages.difference(covered_packages)
    return PackageCoverageResult(
        discovered_packages=discovered_packages,
        covered_packages=covered_packages,
        missing_packages=missing_packages,
        success=not missing_packages,
    )


def validate_reference(
    reference: str,
    *,
    exists: bool,
    complete: bool = True,
) -> ReferenceValidationResult:
    """Assign a status tag to a reference based on its completeness."""

    if not exists:
        status = ReferenceStatus.SUSPECT
    elif not complete:
        status = ReferenceStatus.INCOMPLETE
    else:
        status = ReferenceStatus.CORRECT

    return ReferenceValidationResult(
        reference=reference,
        status=status,
        exists=exists,
        complete=complete,
    )


def parse_quality_tool_health(report_text: str) -> tuple[ToolHealthResult, ...]:
    """Parse tool-health rows from the quality audit report."""

    rows = _table_rows(report_text, "## Tool Results")
    tool_health: list[ToolHealthResult] = []
    for cells in rows:
        if len(cells) < 2:
            continue
        tool_name = _normalize_tool_name(cells[0])
        if not tool_name:
            continue
        tool_health.append(
            ToolHealthResult(
                tool=tool_name,
                status=_normalize_status(cells[1]),
                source_audit="quality",
            )
        )
    return tuple(tool_health)


def parse_tests_tool_health(report_text: str) -> tuple[ToolHealthResult, ...]:
    """Parse pytest execution health from the tests audit report."""

    rows = _table_rows(report_text, "## Execution Evidence")
    if not rows:
        return ()

    status = "PASS"
    for cells in rows:
        if len(cells) < 4:
            continue
        exit_code = cells[3].strip().lower()
        if exit_code not in {"0", ""}:
            status = "FAIL"
            break
    return (
        ToolHealthResult(
            tool="pytest",
            status=status,
            source_audit="tests",
        ),
    )


def parse_rules_report_summary(report_text: str) -> RulesReportSummary:
    """Parse severity totals, recurring rule IDs, and coverage details."""

    severity_counts = {"critical": 0, "important": 0, "minor": 0}
    for cells in _table_rows(report_text, "## Severity Summary"):
        if len(cells) < 2:
            continue
        severity = cells[0].strip().lower()
        if severity not in severity_counts:
            continue
        severity_counts[severity] = _parse_int(cells[1], default=0)

    rule_counts: dict[str, int] = {}
    for cells in _table_rows(report_text, "## Findings"):
        if len(cells) < 3:
            continue
        rule_id = cells[2].strip().strip("`")
        if not rule_id or rule_id == "none":
            continue
        rule_counts[rule_id] = rule_counts.get(rule_id, 0) + 1

    coverage_status = _parse_coverage_status(report_text)
    return RulesReportSummary(
        critical=severity_counts["critical"],
        important=severity_counts["important"],
        minor=severity_counts["minor"],
        top_misalignments=tuple(
            RuleMisalignment(rule_id=rule_id, count=count)
            for rule_id, count in sorted(
                rule_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )[:5]
        ),
        discovered_packages=_parse_bullet_count(report_text, "Discovered packages"),
        covered_packages=_parse_bullet_count(report_text, "Covered packages"),
        missing_packages=_parse_missing_packages(report_text),
        coverage_status=coverage_status,
    )


def has_quality_evidence(report_text: str) -> bool:
    """Return whether the quality report exposes tool results."""

    return bool(parse_quality_tool_health(report_text))


def has_tests_evidence(report_text: str) -> bool:
    """Return whether the tests report exposes execution evidence."""

    return bool(_table_rows(report_text, "## Execution Evidence"))


def _table_rows(report_text: str, heading: str) -> tuple[tuple[str, ...], ...]:
    """Return data rows for the markdown table under a heading."""

    lines = report_text.splitlines()
    start_index: int | None = None
    for index, line in enumerate(lines):
        if line.strip() == heading:
            start_index = index + 1
            break
    if start_index is None:
        return ()

    table_lines: list[str] = []
    for line in lines[start_index:]:
        stripped = line.strip()
        if not stripped:
            if table_lines:
                break
            continue
        if not stripped.startswith("|"):
            if table_lines:
                break
            continue
        table_lines.append(stripped)

    if len(table_lines) < 3:
        return ()

    data_rows: list[tuple[str, ...]] = []
    for row in table_lines[2:]:
        cells = tuple(cell.strip() for cell in row.strip("|").split("|"))
        if cells:
            data_rows.append(cells)
    return tuple(data_rows)


def _normalize_tool_name(value: str) -> str:
    """Normalize tool names to lowercase dashboard keys."""

    return value.strip().strip("`").strip("*").lower()


def _normalize_status(value: str) -> str:
    """Normalize markdown-embellished statuses to plain PASS/FAIL text."""

    cleaned = value.replace("*", "").strip().upper()
    if cleaned in {"PASS", "FAIL"}:
        return cleaned
    return cleaned or "UNKNOWN"


def _parse_int(value: str, *, default: int) -> int:
    """Parse the first integer present in a markdown cell."""

    match = re.search(r"-?\d+", value)
    if match is None:
        return default
    return int(match.group(0))


def _parse_bullet_count(report_text: str, label: str) -> int | None:
    """Parse an integer bullet value from a markdown report."""

    match = re.search(rf"-\s+{re.escape(label)}:\s+(\d+)", report_text)
    if match is None:
        return None
    return int(match.group(1))


def _parse_coverage_status(report_text: str) -> bool | None:
    """Parse the package-coverage PASS/FAIL marker from the rules report."""

    match = re.search(r"-\s+Coverage status:\s+\*\*(PASS|FAIL)\*\*", report_text)
    if match is None:
        return None
    return match.group(1) == "PASS"


def _parse_missing_packages(report_text: str) -> tuple[str, ...]:
    """Parse missing-package bullets from the rules audit."""

    lines = report_text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() != "### Missing Packages":
            continue
        packages: list[str] = []
        for candidate in lines[index + 1 :]:
            stripped = candidate.strip()
            if not stripped:
                if packages:
                    break
                continue
            if not stripped.startswith("- "):
                if packages:
                    break
                continue
            value = stripped[2:].strip().strip("`")
            if value and value != "(none)":
                packages.append(value)
        return tuple(packages)
    return ()
