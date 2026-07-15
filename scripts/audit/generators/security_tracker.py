from __future__ import annotations

from dataclasses import dataclass
import re

_SEVERITY_RE = re.compile(
    "(critical|high|medium|med|low)\\s*\u00d7\\s*(\\d+)", re.IGNORECASE
)
_DONE_RE = re.compile(r"executed|\bdone\b", re.IGNORECASE)
_VERIFIED_CLEAN_HEADING = "verified-clean surfaces"
_SEVERITY_ALIASES = {"medium": "Med", "med": "Med"}


@dataclass(frozen=True, slots=True)
class TrackerRow:
    """One numbered finding row from the audit tracker's markdown tables."""

    number: int
    area: str
    severity_mix: str
    spec: str
    plan: str
    status: str


def parse_tracker_rows(text: str) -> tuple[TrackerRow, ...]:
    """Parse numbered finding rows from every table in the tracker markdown.

    Handles both the 5-column shape (`# | Area | Severity mix | Spec | Plan`)
    and the 6-column shape (`# | Area | §ref | Severity mix | Spec | Plan`).
    """

    rows: list[TrackerRow] = []
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.split("|")]
        data = cells[1:-1]
        if not data or not data[0].isdigit():
            continue
        number = int(data[0])
        area = data[1]
        severity_mix, spec, plan = "", "", ""
        for cell in data[2:]:
            if re.fullmatch(r"§\d+", cell):
                continue
            if _looks_like_severity(cell):
                severity_mix = cell
            elif cell.startswith("`specs/"):
                spec = cell
            else:
                plan = f"{plan} {cell}".strip()
        if not severity_mix and not spec and not plan:
            continue
        row = TrackerRow(number, area, severity_mix, spec, plan, "open")
        rows.append(
            TrackerRow(
                number=number,
                area=area,
                severity_mix=severity_mix,
                spec=spec,
                plan=plan,
                status="done" if row_is_done(row) else "open",
            )
        )
    return tuple(sorted(rows, key=lambda row: row.number))


def parse_verified_clean(text: str) -> tuple[str, ...]:
    """Extract bullet texts under the first 'Verified-clean surfaces' heading."""

    lines = text.splitlines()
    start: int | None = None
    for index, line in enumerate(lines):
        if line.lstrip().startswith("###") and _VERIFIED_CLEAN_HEADING in line.lower():
            start = index + 1
            break
    if start is None:
        return ()
    bullets: list[str] = []
    for line in lines[start:]:
        if line.startswith("##"):
            break
        if line.startswith("###") and _VERIFIED_CLEAN_HEADING not in line.lower():
            break
        if line.startswith("- "):
            bullets.append(line[2:].strip())
    return tuple(bullets)


def severity_counts(severity_mix: str) -> dict[str, int]:
    """Count findings per severity from a raw mix string like 'Critical ×3, High ×2'."""

    counts: dict[str, int] = {}
    for match in _SEVERITY_RE.finditer(severity_mix):
        level = _SEVERITY_ALIASES.get(match.group(1).lower(), match.group(1).capitalize())
        counts[level] = counts.get(level, 0) + int(match.group(2))
    return counts


def row_is_done(row: TrackerRow) -> bool:
    """Return whether a row's spec/plan text marks it executed or done."""

    return bool(_DONE_RE.search(f"{row.spec} {row.plan}"))


def _looks_like_severity(cell: str) -> bool:
    """Return whether a table cell is a severity-mix cell."""

    return bool(re.search("\u00d7", cell)) or bool(
        re.fullmatch("(critical|high|medium|med|low)(\\s*\u00d7\\s*\\d+)?", cell, re.IGNORECASE)
    )
