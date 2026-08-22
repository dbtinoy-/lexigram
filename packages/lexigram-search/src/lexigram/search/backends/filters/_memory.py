"""In-memory predicate rendering."""

from __future__ import annotations

from typing import Any

from lexigram.search.backends.filters._validation import (
    _validate_filters,
)


def render_memory(filters: dict[str, Any]) -> dict[str, Any]:
    """Pass a filter dict through unchanged after validation.

    In-memory backends keep the canonical dialect as their native form.

    Args:
        filters: Canonical filter dict.

    Returns:
        The same filter dict.

    Raises:
        FilterRenderError: If the filter dict violates the dialect.
    """
    _validate_filters(filters)
    return filters
