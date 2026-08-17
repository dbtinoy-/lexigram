"""URL state management for lexigram-admin.

Provides utilities for managing URL state in HTMX applications,
including filters, sorting, pagination, and other query parameters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

if TYPE_CHECKING:
    from starlette.requests import Request


@dataclass
class URLState:
    """Represents the current URL state for admin views.

    Captures all query parameters that affect the view:
    - Pagination: page, per_page
    - Sorting: sort, order
    - Filtering: Various filter parameters
    - Search: q (search query)
    - View options: columns, view_mode

    URLState is immutable - methods return new instances.
    """

    # Pagination
    page: int = 1
    per_page: int = 20
    cursor: str | None = None

    # Sorting
    sort: str | None = None
    order: str = "asc"  # "asc" or "desc"

    # Search
    search: str | None = None

    # Filters (field -> value or [values])
    filters: dict[str, Any] = field(default_factory=dict)

    # View options
    columns: list[str] = field(default_factory=list)
    view_mode: str = "table"  # "table", "grid", "list"

    # Expanded/selected items (for optimistic UI)
    expanded: list[str] = field(default_factory=list)
    selected: list[str] = field(default_factory=list)

    @classmethod
    def from_request(cls, request: Request) -> URLState:
        """Create URLState from request query parameters."""
        params = dict(request.query_params)

        # Parse pagination
        page = int(params.get("page", 1))
        per_page = int(params.get("per_page", 20))
        cursor = params.get("cursor")

        # Parse sorting
        sort = params.get("sort")
        order = params.get("order", "asc")
        if order not in ("asc", "desc"):
            order = "asc"

        # Parse search
        search = params.get("q") or params.get("search")

        # Parse filters (filter_field = value pattern)
        filters: dict[str, Any] = {}
        for key, value in params.items():
            if key.startswith("filter_"):
                field_name = key[7:]
                # Handle multiple values
                if "," in value:
                    filters[field_name] = value.split(",")
                else:
                    filters[field_name] = value

        # Parse columns
        columns: list[str] = []
        if "columns" in params:
            columns = params["columns"].split(",")

        # Parse view mode
        view_mode = params.get("view", "table")

        # Parse expanded/selected
        expanded = (
            params.get("expanded", "").split(",") if params.get("expanded") else []
        )
        selected = (
            params.get("selected", "").split(",") if params.get("selected") else []
        )

        return cls(
            page=page,
            per_page=per_page,
            cursor=cursor,
            sort=sort,
            order=order,
            search=search,
            filters=filters,
            columns=columns,
            view_mode=view_mode,
            expanded=expanded,
            selected=selected,
        )

    def to_query_string(self) -> str:
        """Convert to URL query string."""
        params: dict[str, str] = {}

        # Pagination (only if not defaults)
        if self.cursor:
            params["cursor"] = self.cursor
        elif self.page != 1:
            params["page"] = str(self.page)
        if self.per_page != 20:
            params["per_page"] = str(self.per_page)

        # Sorting
        if self.sort:
            params["sort"] = self.sort
            if self.order != "asc":
                params["order"] = self.order

        # Search
        if self.search:
            params["q"] = self.search

        # Filters
        for field_name, value in self.filters.items():
            if isinstance(value, list):
                params[f"filter_{field_name}"] = ",".join(str(v) for v in value)
            else:
                params[f"filter_{field_name}"] = str(value)

        # Columns
        if self.columns:
            params["columns"] = ",".join(self.columns)

        # View mode
        if self.view_mode != "table":
            params["view"] = self.view_mode

        return urlencode(params)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "page": self.page,
            "per_page": self.per_page,
            "sort": self.sort,
            "order": self.order,
            "search": self.search,
            "filters": self.filters,
            "columns": self.columns,
            "view_mode": self.view_mode,
            "expanded": self.expanded,
            "selected": self.selected,
        }

    # Immutable update methods

    def with_page(self, page: int) -> URLState:
        """Return new state with different page."""
        return URLState(
            page=page,
            per_page=self.per_page,
            sort=self.sort,
            order=self.order,
            search=self.search,
            filters=dict(self.filters),
            columns=list(self.columns),
            view_mode=self.view_mode,
            expanded=list(self.expanded),
            selected=list(self.selected),
        )

    def with_sort(self, sort: str, order: str = "asc") -> URLState:
        """Return new state with different sort."""
        return URLState(
            page=1,  # Reset to first page on sort change
            per_page=self.per_page,
            sort=sort,
            order=order,
            search=self.search,
            filters=dict(self.filters),
            columns=list(self.columns),
            view_mode=self.view_mode,
            expanded=list(self.expanded),
            selected=list(self.selected),
        )

    def with_filter(self, field: str, value: Any) -> URLState:
        """Return new state with filter added/updated."""
        new_filters = dict(self.filters)
        if value is None:
            new_filters.pop(field, None)
        else:
            new_filters[field] = value

        return URLState(
            page=1,  # Reset to first page on filter change
            per_page=self.per_page,
            sort=self.sort,
            order=self.order,
            search=self.search,
            filters=new_filters,
            columns=list(self.columns),
            view_mode=self.view_mode,
            expanded=list(self.expanded),
            selected=list(self.selected),
        )

    def with_search(self, search: str | None) -> URLState:
        """Return new state with search term."""
        return URLState(
            page=1,  # Reset to first page on search
            per_page=self.per_page,
            sort=self.sort,
            order=self.order,
            search=search,
            filters=dict(self.filters),
            columns=list(self.columns),
            view_mode=self.view_mode,
            expanded=list(self.expanded),
            selected=list(self.selected),
        )

    def clear_filters(self) -> URLState:
        """Return new state with all filters cleared."""
        return URLState(
            page=1,
            per_page=self.per_page,
            sort=self.sort,
            order=self.order,
            search=self.search,
            filters={},
            columns=list(self.columns),
            view_mode=self.view_mode,
            expanded=list(self.expanded),
            selected=list(self.selected),
        )

    def toggle_expanded(self, item_id: str) -> URLState:
        """Toggle an item's expanded state."""
        new_expanded = list(self.expanded)
        if item_id in new_expanded:
            new_expanded.remove(item_id)
        else:
            new_expanded.append(item_id)

        return URLState(
            page=self.page,
            per_page=self.per_page,
            sort=self.sort,
            order=self.order,
            search=self.search,
            filters=dict(self.filters),
            columns=list(self.columns),
            view_mode=self.view_mode,
            expanded=new_expanded,
            selected=list(self.selected),
        )

    def toggle_selected(self, item_id: str) -> URLState:
        """Toggle an item's selected state."""
        new_selected = list(self.selected)
        if item_id in new_selected:
            new_selected.remove(item_id)
        else:
            new_selected.append(item_id)

        return URLState(
            page=self.page,
            per_page=self.per_page,
            sort=self.sort,
            order=self.order,
            search=self.search,
            filters=dict(self.filters),
            columns=list(self.columns),
            view_mode=self.view_mode,
            expanded=list(self.expanded),
            selected=new_selected,
        )

    def select_all(self, ids: list[str]) -> URLState:
        """Select all given IDs."""
        return URLState(
            page=self.page,
            per_page=self.per_page,
            sort=self.sort,
            order=self.order,
            search=self.search,
            filters=dict(self.filters),
            columns=list(self.columns),
            view_mode=self.view_mode,
            expanded=list(self.expanded),
            selected=list(ids),
        )

    def clear_selection(self) -> URLState:
        """Clear all selections."""
        return URLState(
            page=self.page,
            per_page=self.per_page,
            sort=self.sort,
            order=self.order,
            search=self.search,
            filters=dict(self.filters),
            columns=list(self.columns),
            view_mode=self.view_mode,
            expanded=list(self.expanded),
            selected=[],
        )


def url_for_state(
    base_url: str,
    state: URLState,
    **overrides: Any,
) -> str:
    """Generate URL with state as query parameters.

    Args:
        base_url: Base URL without query string
        state: Current URL state
        **overrides: Override specific state values

    Returns:
        Full URL with query string
    """
    # Apply overrides
    if overrides:
        state_dict = state.to_dict()
        state_dict.update(overrides)
        state = URLState(**state_dict)

    query_string = state.to_query_string()
    if query_string:
        return f"{base_url}?{query_string}"
    return base_url


def htmx_url_attributes(
    url: str,
    target: str = "#content",
    swap: str = "innerHTML",
    push_url: bool = True,
) -> str:
    """Generate HTMX attributes for URL navigation.

    Args:
        url: Target URL
        target: HTMX target selector
        swap: HTMX swap strategy
        push_url: Whether to push URL to history

    Returns:
        String of HTMX attributes
    """
    attrs = [
        f'hx-get="{url}"',
        f'hx-target="{target}"',
        f'hx-swap="{swap}"',
    ]

    if push_url:
        attrs.append(f'hx-push-url="{url}"')

    return " ".join(attrs)
