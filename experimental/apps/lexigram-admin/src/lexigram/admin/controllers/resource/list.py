"""List view and query building for the resource controller."""

from __future__ import annotations

from typing import Any

from starlette.requests import Request
from starlette.responses import HTMLResponse, Response

from lexigram.admin.controllers.resource.meta import ResourceMeta, T
from lexigram.admin.data.data_source import QueryResult
from lexigram.admin.data.query import QuerySpec
from lexigram.admin.state.context import AdminContext, AdminContextManager
from lexigram.admin.state.url import URLState
from lexigram.ui import el, render_to_string


class ResourceListMixin:
    """List view, query building, and list rendering."""

    # Host attributes provided by sibling mixins on ResourceController.
    meta: ResourceMeta

    get_data_source: Any

    async def list_view(self, request: Request) -> Response:
        """List resources with pagination and filtering."""
        async with AdminContextManager(request) as ctx:
            # Parse URL state
            url_state = URLState.from_request(request)

            # Build query
            query = self._build_query(url_state)

            # Fetch data
            data_source = self.get_data_source()
            result = await data_source.find_many(query)

            # Check if HTMX request
            if ctx.is_htmx:
                # Return just the table/content
                return HTMLResponse(self.render_list_partial(ctx, result, url_state))

            # Return full page
            return HTMLResponse(self.render_list(ctx, result, url_state))

    def _build_query(self, state: URLState) -> QuerySpec:
        """Build QuerySpec from URL state."""
        qs = QuerySpec()

        # Pagination — cursor takes priority over page number
        if state.cursor:
            qs = qs.with_cursor(state.cursor).with_per_page(
                state.per_page or self.meta.per_page
            )
        else:
            qs = qs.with_page(state.page).with_per_page(
                state.per_page or self.meta.per_page
            )

        # Sorting
        if state.sort:
            qs = qs.with_order_by(state.sort, state.order)
        else:
            qs = qs.with_order_by(self.meta.default_sort, self.meta.default_sort_order)

        # Search
        if state.search:
            qs = qs.with_search(state.search, self.meta.searchable_fields or [])

        # Filters
        for field, value in state.filters.items():
            if isinstance(value, list):
                qs = qs.with_where_in(field, value)
            else:
                qs = qs.with_where_eq(field, value)

        return qs

    def render_list(
        self,
        ctx: AdminContext,
        result: QueryResult[T],
        state: URLState,
    ) -> str:
        """Render full list page. Override in subclass."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>{self.meta.label_plural}</title>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
</head>
<body>
    <h1>{self.meta.label_plural}</h1>
    {self.render_list_partial(ctx, result, state)}
</body>
</html>
"""

    def render_list_partial(
        self,
        ctx: AdminContext,
        result: QueryResult[T],
        state: URLState,
    ) -> str:
        """Render list content (for HTMX). Override in subclass."""
        row_els: list[Any] = []
        for item in result.items:
            row_els.append(el("tr", el("td", str(item))))

        total_pages = getattr(result, "total_pages", "?")
        return f"""
<table>
    <thead><tr><th>Item</th></tr></thead>
    {render_to_string(el("tbody", *row_els))}
</table>
<div>Page {result.page} of {total_pages}</div>
"""
