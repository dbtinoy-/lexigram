from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Literal, cast

from htpy import input as htpy_input

from lexigram.domain import DomainModel
from lexigram.ui.state_parsing import parse_table_state
from lexigram.validation import Field


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
    density: Literal["compact", "normal", "comfortable"] = "normal"
    hidden_columns: list[str] = Field(default_factory=list)

    # Internal defaults for clean URL generation (not part of model fields)
    _defaults: ClassVar[dict] = {}

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self._normalize_state()
        if "_defaults" not in self.__dict__:
            object.__setattr__(self, "_defaults", {})

    def _normalize_state(self) -> None:
        """Normalize state values after construction and immutable copying."""
        # ``model_copy(update=...)`` intentionally skips validation in the
        # domain model implementation, so the invariant must be restored on
        # every transition as well as at initial construction.
        try:
            page = max(1, int(self.page))
        except (TypeError, ValueError):
            page = 1
        try:
            per_page = max(1, min(int(self.per_page), 1000))
        except (TypeError, ValueError):
            per_page = 20
        object.__setattr__(self, "page", page)
        object.__setattr__(self, "per_page", per_page)

        if self.sort_order not in ("asc", "desc"):
            object.__setattr__(self, "sort_order", "asc")
        if self.view not in ("tabular", "grid", "calendar", "stacked"):
            object.__setattr__(self, "view", "tabular")
        if self.layout not in ("sidebar", "stack"):
            object.__setattr__(self, "layout", "stack")
        if self.density not in ("compact", "normal", "comfortable"):
            object.__setattr__(self, "density", "normal")
        object.__setattr__(self, "filters", dict(self.filters or {}))
        object.__setattr__(
            self,
            "collapsed_groups",
            list(self.collapsed_groups or []),
        )
        object.__setattr__(self, "hidden_columns", list(self.hidden_columns or []))
        if self.column_order is not None:
            object.__setattr__(self, "column_order", list(self.column_order))

    @classmethod
    def from_request(cls, request: Any, defaults: dict | None = None) -> TableState:
        """
        Create state from a request object (Starlette/ASGI compatible).
        """
        return parse_table_state(cls, request, defaults)

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
        add("density", self.density, "normal")

        if self.cursor:
            add("cursor", self.cursor)
        if self.column_order:
            add("col_order", ",".join(self.column_order))
        if self.hidden_columns:
            add("hide_cols", ",".join(self.hidden_columns))
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
        """Override model_copy to preserve defaults and state invariants."""
        new_state = super().model_copy(*args, **kwargs)
        new_state._normalize_state()
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
        return self.model_copy(
            update={
                "per_page": max(1, int(per_page)),
                "page": 1,
                "cursor": None,
            }
        )

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
            return self.model_copy(
                update={"sort_order": new_order, "page": 1, "cursor": None}
            )
        return self.model_copy(
            update={
                "sort_by": column,
                "sort_order": "asc",
                "page": 1,
                "cursor": None,
            }
        )

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

    def with_density(
        self,
        density: Literal["compact", "normal", "comfortable"],
    ) -> TableState:
        """Return a copy with a new row density.

        Density only affects presentation (row height / spacing), not the
        result set, so pagination state is preserved.

        Example:
            new_state = state.with_density("compact")
        """
        return self.model_copy(update={"density": density})

    def with_hidden_columns(self, hidden_columns: list[str]) -> TableState:
        """Return a copy with the given set of hidden column names.

        Column visibility is presentation-only, so pagination state is
        preserved.

        Example:
            new_state = state.with_hidden_columns(["secret", "internal_note"])
        """
        return self.model_copy(update={"hidden_columns": list(hidden_columns)})

    def toggle_column(self, column: str) -> TableState:
        """Return a copy with the visibility of ``column`` toggled.

        Hides the column when it is currently visible, and reveals it when
        it is currently hidden. Other hidden columns are preserved.

        Example:
            toggled = state.toggle_column("email")
        """
        hidden = list(self.hidden_columns or [])
        if column in hidden:
            hidden.remove(column)
        else:
            hidden.append(column)
        return self.with_hidden_columns(hidden)

    def is_column_hidden(self, column: str) -> bool:
        """Return whether ``column`` is currently hidden."""
        return column in (self.hidden_columns or [])

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
        """Return a copy with sorting cleared and pagination reset."""
        return self.model_copy(
            update={
                "sort_by": None,
                "sort_order": "asc",
                "page": 1,
                "cursor": None,
            }
        )

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
