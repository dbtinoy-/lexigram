"""Parsing and comparison of documentation default-value claims."""

from __future__ import annotations

from enum import Enum
import re

from dev.audit.generators.docs_defaults.universe import (
    _KIND_LITERAL,
    _UNPARSEABLE_CELL,
    DefaultEntry,
)

_NUMERIC = (int, float)


def _parse_claim_value(raw: str) -> tuple[bool, object]:
    """Parse a doc-stated default into a comparable scalar (or not)."""
    value = raw.strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        value = value[1:-1].strip()
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        if len(value) >= 2:
            return True, value[1:-1]
        return False, None
    lower = value.lower()
    if lower in ("true", "false"):
        return True, lower == "true"
    if lower in ("none", "null"):
        return True, None
    try:
        return True, int(value)
    except ValueError:
        pass
    try:
        return True, float(value)
    except ValueError:
        pass
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_.\-]*", value):
        return True, value
    return False, None


def _defaults_equal(claimed: object, real: object) -> bool | None:
    """Compare a parsed claim with a real default; None when not comparable."""
    if isinstance(real, Enum):
        return None
    if isinstance(real, bool):
        return claimed == real if isinstance(claimed, bool) else None
    if isinstance(real, _NUMERIC):
        return claimed == real if isinstance(claimed, _NUMERIC) else None
    if isinstance(real, str):
        return claimed == real if isinstance(claimed, str) else None
    if real is None:
        return claimed is None
    return None


_HINT_RE = re.compile(
    r"\b[A-Z][A-Za-z0-9_]*(?:Config|Contributor|Resource|Options|Spec|Settings)\b"
)


def _doc_class_hints(md_text: str) -> frozenset[str]:
    """Class names a doc mentions (config/resource-style), used to disambiguate."""
    return frozenset(_HINT_RE.findall(md_text))


def _unique_comparable_default(
    entries: list[DefaultEntry],
    hints: frozenset[str] = frozenset(),
) -> tuple[bool, object | None, list[DefaultEntry]]:
    """Return (unambiguous, default, comparable entries) for candidates.

    When multiple distinct defaults exist, doc-mentioned class names (``hints``)
    narrow the candidate set; if that leaves one distinct default, the claim is
    verified against it.
    """
    comparable = [e for e in entries if e.kind == _KIND_LITERAL]
    if not comparable:
        return False, None, []
    defaults = {repr(e.default) for e in comparable}
    if len(defaults) == 1:
        return True, comparable[0].default, comparable
    hinted = [
        e
        for e in comparable
        if e.class_name in hints or any(p in hints for p in e.parents)
    ]
    if hinted:
        hinted_defaults = {repr(e.default) for e in hinted}
        if len(hinted_defaults) == 1:
            return True, hinted[0].default, hinted
    return False, None, comparable


_INLINE_WITH_KEY_RE = re.compile(
    r"(?<![\w.`])([A-Za-z_][\w.]*)\s*\(default[:=]\s*([^)]+)\)", re.I
)
_INLINE_BARE_RE = re.compile(r"\(default[:=]\s*([^)]+)\)", re.I)
_DEFAULTS_TO_RE = re.compile(
    r"(?<![\w.`])([A-Za-z_][\w.]*)\s+defaults?\s+(?:to|is)\s+([^,.;\n):]+)", re.I
)
_INLINE_KEY_RE = re.compile(r"[\w.]*$")


def _claim_text(raw: str) -> str:
    text = raw.strip()
    if text.startswith("`") and text.endswith("`"):
        text = text[1:-1]
    return text.strip()


def _iter_claims(md_text: str) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Extract (key, claimed-value) claims from tables and from prose.

    Returns (table_claims, prose_claims); prose claims exclude lines that
    belong to a parsed table to avoid double-counting inline annotations.
    """
    lines = md_text.splitlines()
    table_claims: list[tuple[str, str]] = []
    prose_claims: list[tuple[str, str]] = []
    in_table_lines: set[int] = set()

    i = 0
    while i < len(lines) - 1:
        header = lines[i]
        if not header.startswith("|") or not lines[i + 1].startswith("|"):
            i += 1
            continue
        if not re.fullmatch(r"\|[\s\-:|]+", lines[i + 1]):
            i += 1
            continue
        cells = [c.strip() for c in header.strip("|").split("|")]
        if not cells:
            i += 1
            continue
        default_col = next(
            (idx for idx, cell in enumerate(cells) if "default" in cell.lower()), None
        )
        env_col = next(
            (
                idx
                for idx, cell in enumerate(cells)
                if re.search(r"env\s*var", cell.lower())
            ),
            None,
        )
        row_start = i + 2
        while row_start < len(lines) and lines[row_start].startswith("|"):
            in_table_lines.add(row_start)
            row_cells = [c.strip() for c in lines[row_start].strip("|").split("|")]
            while len(row_cells) < len(cells):
                row_cells.append("")
            if default_col is not None and default_col < len(row_cells):
                key = _claim_text(row_cells[0]) if row_cells else ""
                claimed = _claim_text(row_cells[default_col])
                if not key or not claimed or claimed.lower() in _UNPARSEABLE_CELL:
                    row_start += 1
                    continue
                if env_col is not None and env_col < len(row_cells):
                    env_cell = _claim_text(row_cells[env_col])
                    if env_cell and env_cell.lower() not in _UNPARSEABLE_CELL:
                        table_claims.append((env_cell, claimed))
                        row_start += 1
                        continue
                table_claims.append((key, claimed))
            row_start += 1
        i = row_start

    for idx, line in enumerate(lines):
        if idx in in_table_lines or line.startswith("```"):
            continue
        if line in ("```",) or line.startswith("```"):
            continue
        for match in _INLINE_WITH_KEY_RE.finditer(line):
            prose_claims.append((match.group(1), match.group(2)))
        for match in _INLINE_BARE_RE.finditer(line):
            prefix = line[: match.start()]
            key_match = _INLINE_KEY_RE.search(prefix)
            if key_match and key_match.group(0):
                prose_claims.append((key_match.group(0), match.group(1)))
        for match in _DEFAULTS_TO_RE.finditer(line):
            prose_claims.append((match.group(1), match.group(2)))
    return table_claims, prose_claims
