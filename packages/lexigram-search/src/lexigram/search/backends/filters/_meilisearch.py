"""Meilisearch filter rendering."""

from __future__ import annotations

from typing import Any

from lexigram.search.backends.filters._validation import (
    _COMPARISON_SYMBOLS,
    FilterRenderError,
    _validate_filters,
)


def _meili_value(value: Any) -> str:
    """Format a scalar as a Meilisearch filter literal.

    String literals are ``"``-delimited with embedded backslashes and
    double quotes backslash-escaped (backslash first), so caller-supplied
    values can never terminate the literal. Booleans and numbers stay
    unquoted.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _meili_expr(sub: dict[str, Any]) -> str:
    """Render one sub-filter dict to an atomic Meilisearch expression.

    Group children are parenthesized. Lone ``$or``/``$and`` groups and
    single-condition frames are returned bare, so a top-level group does
    not gain stray outer parentheses.
    """
    many = len(sub) > 1
    parts: list[str] = []
    for key, value in sub.items():
        if key == "$not":
            if not isinstance(value, dict):
                raise FilterRenderError("$not must contain a single filter dict")
            parts.append(f"NOT ({_meili_expr(value)})")
            continue
        if key in ("$and", "$or"):
            if not isinstance(value, list):
                raise FilterRenderError(f"{key} must be a list of filter dicts")
            rendered = [f"({_meili_expr(group)})" for group in value]
            joined = " OR ".join(rendered) if key == "$or" else " AND ".join(rendered)
            parts.append(f"({joined})" if many else joined)
            continue
        if isinstance(value, dict):
            if "contains" in value:
                # Meilisearch filters only support equality/prefix matching;
                # "contains" degrades to a prefix equality filter.
                parts.append(f"{key} = {_meili_value(value['contains'])}")
                continue
            if "exists" in value:
                raise FilterRenderError(
                    "'exists' cannot be expressed in a Meilisearch filter"
                )
            if "in" in value:
                members = ", ".join(_meili_value(v) for v in value["in"])
                parts.append(f"{key} IN [{members}]")
                continue
            if "nin" in value:
                members = ", ".join(_meili_value(v) for v in value["nin"])
                parts.append(f"{key} NOT IN [{members}]")
                continue
            if "ne" in value:
                parts.append(f"{key} != {_meili_value(value['ne'])}")
                continue
            comparisons = [
                f"{key} {_COMPARISON_SYMBOLS[op]} {_meili_value(val)}"
                for op, val in value.items()
            ]
            parts.append(" and ".join(comparisons))
            continue
        if isinstance(value, (list, tuple)):
            members = ", ".join(_meili_value(v) for v in value)
            parts.append(f"{key} IN [{members}]")
        else:
            parts.append(f"{key} = {_meili_value(value)}")
    joined = " AND ".join(parts)
    return joined


def render_meilisearch(filters: dict[str, Any]) -> str:
    """Render a filter dict to a Meilisearch ``filter`` expression string.

    Args:
        filters: Canonical filter dict.

    Returns:
        A Meilisearch filter expression (``"status = \\"active\\""``,
        ``"score >= 80"``, ``"(a) OR (b)"``, ...).

    Raises:
        FilterRenderError: If the filter dict violates the dialect or uses
            an operator Meilisearch cannot express.
    """
    _validate_filters(filters)
    return _meili_expr(filters)


# ---------------------------------------------------------------------------
# Typesense (filter-expression string)
# ---------------------------------------------------------------------------
