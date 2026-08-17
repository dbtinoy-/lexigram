from __future__ import annotations

from typing import Any

RISKY_LEADING_CHARS = ("=", "+", "-", "@", "\t", "\r")


def sanitize_cell_value(value: Any) -> Any:
    """Neutralize formula/DDE injection in a single cell value.

    Spreadsheet applications evaluate cells whose leading character is
    ``=``, ``+``, ``-``, ``@``, or a tab/CR as a live formula or DDE
    trigger when an operator opens the exported file (OWASP CSV-injection
    class). Prefix such values with a single quote so they render as text;
    the prefix is lossless — stripping instead would silently corrupt
    legitimate ``-``/``+``-leading data.

    Args:
        value: Raw cell value from the export data source.

    Returns:
        The sanitized value: non-strings and non-risky strings pass
        through unchanged; risky strings gain a leading ``'``.
    """
    if not isinstance(value, str) or not value:
        return value
    if value[0] in RISKY_LEADING_CHARS:
        return f"'{value}"
    return value
