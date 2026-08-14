"""Per-column table summarizers for footer aggregates.

Computes aggregate footer values (sum, average, count, range) for
columns declared with ``Column.summarizer()`` against the currently
visible page of records.
"""

from __future__ import annotations

from typing import Any

SUMMARIZER_LABELS: dict[str, str] = {
    "sum": "Sum",
    "average": "Average",
    "count": "Count",
    "range": "Range",
}

SUMMARIZER_OPERATORS = frozenset(SUMMARIZER_LABELS)


def _column_values(rows: list[Any], column: Any) -> list[Any]:
    """Collect non-empty raw values for a column across records."""
    values: list[Any] = []
    for row in rows:
        value = column.get_value(row)
        if value is None or value == "":
            continue
        values.append(value)
    return values


def _numeric(values: list[Any]) -> list[float]:
    """Coerce values to floats, skipping non-numeric entries."""
    numeric: list[float] = []
    for value in values:
        try:
            numeric.append(float(value))
        except (TypeError, ValueError):
            continue
    return numeric


def _format(number: float) -> str:
    """Format a number without trailing zeros for integral values."""
    if number == int(number):
        return str(int(number))
    return f"{number:.2f}".rstrip("0").rstrip(".")


def compute_summaries(rows: list[Any], columns: list[Any]) -> dict[str, str]:
    """Compute footer summaries for columns with a configured summarizer.

    Args:
        rows: Records on the current page.
        columns: Table columns; only those with ``_summarizer`` set are
            considered.

    Returns:
        Mapping of column name to display string, e.g. ``"Sum 42"``.
        Columns whose data yields no usable values are omitted.
    """
    summaries: dict[str, str] = {}
    for column in columns:
        operator = getattr(column, "_summarizer", None)
        if operator not in SUMMARIZER_OPERATORS:
            continue
        values = _column_values(rows, column)
        label = SUMMARIZER_LABELS[operator]
        if operator == "count":
            summaries[column.name] = f"{label} {len(values)}"
            continue
        numeric = _numeric(values)
        if not numeric:
            continue
        if operator == "sum":
            summaries[column.name] = f"{label} {_format(sum(numeric))}"
        elif operator == "average":
            summaries[column.name] = f"{label} {_format(sum(numeric) / len(numeric))}"
        elif operator == "range":
            summaries[column.name] = (
                f"{label} {_format(min(numeric))} - {_format(max(numeric))}"
            )
    return summaries
