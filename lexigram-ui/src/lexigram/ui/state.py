from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import Any, ClassVar, Literal, cast

from htpy import input as htpy_input

from lexigram.domain import DomainModel
from lexigram.logging import get_logger
from lexigram.validation import Field

logger = get_logger(__name__)


@dataclass(init=False)
class TableState(DomainModel):
    """
    Encapsulates the complete state of a DataTable.
    This state is derived from the URL and drives the UI rendering.
    """

    search: str = ""
    sort_by: str | None = None
    sort_order: Literal["asc", "desc"] = "asc"
    page: int = 1
    per_page: int = 20
    cursor: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    view: Literal["tabular", "grid", "calendar", "stacked"] = "tabular"
    layout: Literal["sidebar", "stack"] = "stack"
    column_order: list[str] | None = None
    group_by: str | None = None
    collapsed_groups: list[str] = Field(default_factory=list)
    include_deleted: bool = False

    # Internal defaults for clean URL generation (not part of model fields)
    _defaults: ClassVar[dict] = {}

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if "_defaults" not in self.__dict__:
            object.__setattr__(self, "_defaults", {})

    @classmethod
    def from_request(cls, request: Any, defaults: dict | None = None) -> TableState:
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
            defaults.get("sort_by")
            if isinstance(defaults.get("sort_by"), str)
            else None
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

        # Extract Filters
        # We assume any param not in this blocklist is a filter
        known_keys = {
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

        col_order_raw = q.get("col_order")
        col_order = (
            col_order_raw.split(",") if col_order_raw else defaults.get("column_order")
        )

        group_by = q.get("group_by", defaults.get("group_by"))
        collapsed_raw = q.get("collapsed_groups", "")
        collapsed_groups = collapsed_raw.split(",") if collapsed_raw else []

        # For filters, we also want the last value if duplicated
        def _coerce_value(val: str) -> Any:
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

        filters = {}
        for k in q:
            if k in known_keys:
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

    def to_query_params(self, exclude: list[str] | None = None) -> dict:
        """
        Export state to dictionary suitable for URL generation.
        Only includes non-default and non-empty values to keep URLs clean.
        """
        exclude = exclude or []
        params = {}

        # Mapping of query param names to state attribute names for default lookup
        key_map = {
            "data_view": "view",
            "layout_type": "layout",
        }

        def add(key: Any, val: Any, default: Any = None) -> Any:
            if key in exclude:
                return

            # Use resource defaults if available for cleaner URLs
            # Map query key to internal state key for defaults lookup
            state_key = key_map.get(key, key)
            res_default = self._defaults.get(state_key, default)

            # Stringify for comparison if needed
            val_str = str(val) if val is not None else ""
            def_str = str(res_default) if res_default is not None else ""

            # Only add if strictly non-default and non-empty
            if val is not None and val_str != def_str and val != "":
                params[key] = val

        add("search", self.search, "")
        add("page", self.page, 1)
        add("per_page", self.per_page, 20)
        add("sort_by", self.sort_by, "")
        add("sort_order", self.sort_order, "asc")
        add("data_view", self.view, "tabular")
        add("layout_type", self.layout, "stack")

        if self.cursor:
            add("cursor", self.cursor)
        if self.column_order:
            add("col_order", ",".join(self.column_order))
        if self.group_by:
            add("group_by", self.group_by)
        if self.collapsed_groups:
            add("collapsed_groups", ",".join(self.collapsed_groups))
        add("include_deleted", self.include_deleted, False)

        # Add filters with prefix (non-empty only)
        for k, v in self.filters.items():
            param_key = f"filter_{k}"
            if (
                param_key not in exclude
                and k not in exclude
                and v is not None
                and v != ""
            ):
                params[param_key] = v

        return params

    def to_url(self, base_path: str = "") -> str:
        """Return a canonical URL (path + query) for this TableState."""
        from urllib.parse import urlencode

        params = self.to_query_params()
        if not base_path:
            base_path = ""
        query = urlencode(params, doseq=True)
        url = base_path or ""
        if query:
            url = f"{url}?{query}"
        return url

    def model_copy(self, *args: Any, **kwargs: Any) -> TableState:
        """Override model_copy to preserve internal defaults."""
        new_state = super().model_copy(*args, **kwargs)
        object.__setattr__(new_state, "_defaults", getattr(self, "_defaults", {}))
        return cast("TableState", new_state)

    # These methods return NEW TableState instances with modified values.
    # The original state is not modified (immutable pattern).

    def with_page(self, page: int) -> TableState:
        """
        Return a copy with a new page number.

        Resets cursor for offset-based pagination.

        Example:
            new_state = state.with_page(2)
            attrs = HTMXAttrs.for_data_refresh(new_state, prefix)
        """
        return self.model_copy(update={"page": page, "cursor": None})

    def with_per_page(self, per_page: int) -> TableState:
        """
        Return a copy with a new per_page value.

        Resets to page 1 since row counts change.
        """
        return self.model_copy(update={"per_page": per_page, "page": 1, "cursor": None})

    def with_search(self, search: str) -> TableState:
        """
        Return a copy with a new search term.

        Resets to page 1 since results change.
        """
        return self.model_copy(update={"search": search, "page": 1, "cursor": None})

    def with_filter(self, key: str, value: Any) -> TableState:
        """
        Return a copy with an updated filter value.

        Resets to page 1 since results change.

        Example:
            new_state = state.with_filter("status", "active")
        """
        new_filters = {**self.filters, key: value}
        return self.model_copy(
            update={"filters": new_filters, "page": 1, "cursor": None},
        )

    def without_filter(self, key: str) -> TableState:
        """
        Return a copy with a filter removed.

        Resets to page 1 since results change.
        """
        new_filters = {k: v for k, v in self.filters.items() if k != key}
        return self.model_copy(
            update={"filters": new_filters, "page": 1, "cursor": None},
        )

    def with_sort(self, column: str) -> TableState:
        """
        Return a copy with sort toggled on the given column.

        If already sorting by this column, toggles direction.
        Otherwise, sets ascending sort on the column.

        Example:
            new_state = state.with_sort("name")  # asc
            new_state = new_state.with_sort("name")  # desc
        """
        if self.sort_by == column:
            new_order = "desc" if self.sort_order == "asc" else "asc"
            return self.model_copy(update={"sort_order": new_order})
        return self.model_copy(update={"sort_by": column, "sort_order": "asc"})

    def with_view(
        self,
        view: Literal["tabular", "grid", "calendar", "stacked"],
    ) -> TableState:
        """Return a copy with a new view type."""
        return self.model_copy(update={"view": view})

    def with_layout(self, layout: Literal["sidebar", "stack"]) -> TableState:
        """Return a copy with a new layout type."""
        return self.model_copy(update={"layout": layout})

    def with_group_by(self, group_by: str | None) -> TableState:
        """Return a copy with a new grouping column.

        Pass ``None`` to clear grouping. Resets to page 1 since
        grouping changes the result set.

        Example:
            new_state = state.with_group_by("category")
            cleared = state.with_group_by(None)
        """
        return self.model_copy(
            update={"group_by": group_by, "page": 1, "cursor": None},
        )

    def with_include_deleted(self, include_deleted: bool) -> TableState:
        """Return a copy with a new include_deleted value.

        Resets to page 1 since results change.

        Example:
            new_state = state.with_include_deleted(True)
        """
        return self.model_copy(
            update={"include_deleted": include_deleted, "page": 1, "cursor": None},
        )

    def clear_filters(self) -> TableState:
        """
        Return a copy with all filters and search cleared.

        Resets to page 1.
        """
        return self.model_copy(
            update={
                "filters": {},
                "search": "",
                "page": 1,
                "cursor": None,
            },
        )

    def clear_sort(self) -> TableState:
        """Return a copy with sorting cleared."""
        return self.model_copy(update={"sort_by": None, "sort_order": "asc"})

    def set_resource_prefix(self, prefix: str) -> None:
        """Set the resource prefix for URL generation."""
        object.__setattr__(self, "_resource_prefix", prefix)

    def get_resource_prefix(self) -> str | None:
        """Get the resource prefix for URL generation."""
        return getattr(self, "_resource_prefix", None)

    # === Hidden Input Rendering ===

    def render_hidden_inputs(self, exclude: list[str] | None = None) -> list:
        """
        Render hidden inputs for state preservation.

        Used as a fallback when baked URLs aren't possible (e.g., form submissions
        that need to preserve table state).

        These inputs should be placed INSIDE the TABLE zone.

        Args:
            exclude: Optional list of field names to skip (avoid duplication with UI inputs)

        Returns:
            List of htpy input elements
        """
        inputs = []
        excluded_keys = set(exclude or [])

        params = self.to_query_params()
        for key, value in params.items():
            if key in excluded_keys:
                continue

            # Handle multi-value fields by rendering multiple hidden inputs
            values = value if isinstance(value, (list, tuple)) else [value]
            for v in values:
                inputs.append(
                    htpy_input(
                        type="hidden",
                        name=key,
                        value=str(v),
                        data_state="true",  # Mark as state input for debugging
                    ),
                )

        return inputs
