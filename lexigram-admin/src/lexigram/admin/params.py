"""Widget parameter parsing — HTTP boundary helpers for admin widget requests."""

from __future__ import annotations

from collections.abc import Mapping

from lexigram.contracts.admin.types import WidgetParams


def parse_widget_params(query: Mapping[str, str]) -> WidgetParams:
    """Parse and validate HTTP query parameters into a typed ``WidgetParams``.

    Clamps values to safe ranges and applies defaults.
    This is the only place where raw HTTP query strings are converted
    to the typed contract object.

    Args:
        query: Raw query string parameters from the HTTP request.

    Returns:
        Validated ``WidgetParams`` with defaults applied for missing keys.
    """
    try:
        page = max(1, int(query.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

    try:
        page_size = min(100, max(1, int(query.get("page_size", 20))))
    except (ValueError, TypeError):
        page_size = 20

    try:
        time_window = max(1, int(query.get("time_window_minutes", 60)))
    except (ValueError, TypeError):
        time_window = 60

    return WidgetParams(
        page=page,
        page_size=page_size,
        time_window_minutes=time_window,
        raw=tuple(query.items()),
    )


__all__ = ["parse_widget_params"]
