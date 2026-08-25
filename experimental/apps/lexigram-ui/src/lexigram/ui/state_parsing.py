"""Request-to-state parsing for :class:`~lexigram.ui.state.TableState`.

Pure parsing helpers consumed by ``TableState.from_request``. Kept separate
from the state value type so the model stays focused on state semantics
while query-string extraction/coercion lives here.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.ui.state import TableState

logger = get_logger(__name__)

# Query params that carry DataTable machinery rather than user filters.
KNOWN_QUERY_KEYS: frozenset[str] = frozenset(
    {
        "collapsed_groups",
        "col_order",
        "data_view",
        "filters",
        "flash_message",
        "flash_type",
        "group_by",
        "hx-current-url",
        "hx-request",
        "hx-target",
        "hx-trigger",
        "ids",
        "include_deleted",
        "layout_type",
        "limit",
        "next",
        "page",
        "per_page",
        "render_fragment",
        "search",
        "select_all",
        "sort_by",
        "sort_order",
    }
)


def _coerce_value(val: str) -> Any:
    """Coerce a raw query-string value to bool/int/float when possible."""
    # Normalize booleans
    if isinstance(val, str):
        low = val.lower()
        if low == "true":
            return True
        if low == "false":
            return False
        # Try integer
        try:
            if val.isdigit() or (val.startswith("-") and val[1:].isdigit()):
                return int(val)
        except (ValueError, TypeError):
            pass
        # Try float
        try:
            if "." in val:
                return float(val)
        except (ValueError, TypeError):
            pass
    return val


def parse_table_state(
    cls: type[TableState],
    request: Any,
    defaults: dict | None = None,
) -> TableState:
    """
    Create state from a request object (Starlette/ASGI compatible).
    """
    defaults = defaults or {}

    # Use request.query_params directly for better multi-value handling.
    # .get() on Starlette QueryParams returns the LAST value by default,
    # which is what we want for overrides (e.g. link ?view=grid overriding hidden input view=tabular).
    q = request.query_params

    # Extract Standard Fields
    search = q.get("search") or ""
    sort_by = q.get("sort_by") or defaults.get("sort_by")
    sort_order = q.get("sort_order") or defaults.get("sort_order", "asc")

    try:
        page = int(q.get("page", 1))
        page = max(page, 1)
    except (ValueError, TypeError):
        page = 1

    try:
        per_page = int(q.get("per_page", 20))
    except (ValueError, TypeError):
        per_page = 20
        # Explicitly check for 'limit' as an alias often used in APIs
        with contextlib.suppress(ValueError, TypeError):
            per_page = int(q.get("limit", 20))

    view = q.get("data_view") or defaults.get("view", "tabular")
    layout = q.get("layout_type") or defaults.get("layout", "stack")
    cursor = q.get("cursor") or None

    include_deleted_raw = q.get("include_deleted", "false")
    include_deleted = include_deleted_raw.lower() == "true"

    # Defensive: resolve defaults (guard against inconsistent test defaults)
    default_sort_by = (
        defaults.get("sort_by") if isinstance(defaults.get("sort_by"), str) else None
    )
    default_sort_order = (
        defaults.get("sort_order", "asc")
        if isinstance(defaults.get("sort_order", "asc"), str)
        else "asc"
    )
    default_view = (
        defaults.get("view", "tabular")
        if isinstance(defaults.get("view", "tabular"), str)
        else "tabular"
    )
    # Normalize defaults with defensive checks and logging (guard against misconfigured app defaults)
    raw_default_layout = defaults.get("layout", "stack")
    if isinstance(raw_default_layout, str):
        if raw_default_layout in ("sidebar", "stack"):
            default_layout = raw_default_layout
        else:
            logger.warning(
                "Unknown default layout '%s' provided; using fallback 'stack'",
                raw_default_layout,
            )
            default_layout = "stack"
    else:
        logger.warning(
            "Non-string default layout provided (%r); using fallback 'stack'",
            raw_default_layout,
        )
        default_layout = "stack"

    # Apply defaults/coercion
    if not isinstance(sort_by, (str, type(None))):
        logger.warning("Invalid default sort_by %r; ignoring", sort_by)
        sort_by = default_sort_by

    if sort_order not in ("asc", "desc"):
        logger.warning(
            "Invalid default sort_order %r; using '%s'",
            sort_order,
            default_sort_order,
        )
        sort_order = default_sort_order

    # Normalize view default
    raw_default_view = defaults.get("view", "tabular")
    if isinstance(raw_default_view, str) and raw_default_view in (
        "tabular",
        "grid",
        "calendar",
        "stacked",
    ):
        default_view = raw_default_view
    else:
        if not isinstance(raw_default_view, str):
            logger.warning(
                "Non-string default view provided (%r); using 'tabular'",
                raw_default_view,
            )
        else:
            logger.warning(
                "Unknown default view '%s' provided; using 'tabular'",
                raw_default_view,
            )
        default_view = "tabular"

    # Normalize incoming 'view' param
    if not isinstance(view, str) or view not in (
        "tabular",
        "grid",
        "calendar",
        "stacked",
    ):
        logger.debug(
            "Invalid or missing request view %r; using default %r",
            view,
            default_view,
        )
        view = default_view

    # GuardProtocol the final layout value
    if not isinstance(layout, str) or layout not in (
        "sidebar",
        "stack",
    ):
        logger.debug(
            "Invalid or missing request layout %r; using default %r",
            layout,
            default_layout,
        )
        layout = default_layout

    col_order_raw = q.get("col_order")
    col_order = (
        col_order_raw.split(",") if col_order_raw else defaults.get("column_order")
    )

    group_by = q.get("group_by", defaults.get("group_by"))
    collapsed_raw = q.get("collapsed_groups", "")
    collapsed_groups = collapsed_raw.split(",") if collapsed_raw else []

    filters = _extract_filters(q)

    state = cls(
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=per_page,
        cursor=cursor,
        filters=filters,
        view=view,
        layout=layout,
        column_order=col_order,
        group_by=group_by,
        collapsed_groups=collapsed_groups,
        include_deleted=include_deleted,
    )
    object.__setattr__(state, "_defaults", defaults or {})
    return state


def _extract_filters(q: Any) -> dict[str, Any]:
    """Extract filter params: any query key not in ``KNOWN_QUERY_KEYS``."""
    filters: dict[str, Any] = {}
    for k in q:
        if k in KNOWN_QUERY_KEYS:
            continue

        filter_key = k[7:] if k.startswith("filter_") else k

        # Support both Starlette QueryParams (with getlist) and plain dicts
        if hasattr(q, "getlist"):
            values = q.getlist(k)
        else:
            v = q.get(k)
            values = [v] if v is not None else []

        if not values:
            continue

        # Filter out empty strings
        values = list(filter(lambda v: v is not None and v != "", values))
        if not values:
            continue

        # Deduplicate values
        unique_values = []
        seen = set()
        for v in values:
            # If it's a string representation of a list, repair it
            if isinstance(v, str) and v.startswith("[") and v.endswith("]"):
                import ast

                try:
                    parsed = ast.literal_eval(v)
                    if isinstance(parsed, list):
                        for item in parsed:
                            val = _coerce_value(str(item))
                            if val not in seen:
                                unique_values.append(val)
                                seen.add(val)
                        continue
                except (TypeError, ValueError):
                    pass

            val = _coerce_value(v)
            if val not in seen:
                unique_values.append(val)
                seen.add(val)
        values = unique_values

        if len(values) > 1:
            filters[filter_key] = values
        elif values:
            filters[filter_key] = values[0]

    return filters
