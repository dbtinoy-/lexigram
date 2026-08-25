from __future__ import annotations

"""List view rendering for admin resources.

Composes the column-spec helpers (:mod:`..list_columns`) and the
paginated data fetcher (:mod:`..list_query`) into the DataTable-driven
list view for an admin resource.
"""

from starlette.responses import HTMLResponse

from lexigram.admin.config import AdminConfig
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.observability.admin_metrics import AdminMetrics
from lexigram.admin.resources.config import TableConfiguration
from lexigram.admin.resources.list_columns import (
    build_columns,
    get_bulk_actions,
    get_filter_options,
    get_header_actions,
    get_row_actions,
)
from lexigram.admin.resources.list_query import ListDataFetcher
from lexigram.admin.state.context import wants_fragment
from lexigram.admin.ui.organisms.data_table import DataTable
from lexigram.di.decorators import inject
from lexigram.ui import TableState, Zones, render_to_string


@inject
class ListRenderer:
    """Handles rendering of list views for admin resources."""

    def __init__(
        self,
        config: AdminConfig,
        resource_name: str,
        renderer: AdminRenderer,
        metrics: AdminMetrics | None = None,
    ):
        self._config = config
        self.resource_name = resource_name
        self._renderer = renderer
        self._metrics = metrics or AdminMetrics(None)
        self._fetcher = ListDataFetcher(resource_name, metrics)

    async def render(
        self,
        request,
        resource,
        user=None,
    ) -> HTMLResponse:
        """Render list view with DataTable component."""
        # Get resource configuration
        table_config = (
            resource.get_table_config()
            if resource and hasattr(resource, "get_table_config")
            else None
        )
        label = (
            (table_config.resource_name if table_config else self.resource_name)
            .replace("_", " ")
            .title()
        )
        resource_prefix = f"{self._config.prefix}/{self.resource_name}"

        # Resolve Columns Early for Search
        source_columns = []
        if table_config and table_config.columns:
            source_columns = table_config.columns
        elif resource and hasattr(resource, "columns"):
            # Check if columns is a property/method
            source_columns = (
                resource.columns
                if not callable(resource.columns)
                else resource.columns()
            )

        # Parse request params using TableState
        state = TableState.from_request(
            request,
            defaults={
                "sort_by": table_config.default_sort_by if table_config else None,
                "sort_order": table_config.default_sort_order
                if table_config
                else "asc",
                "view": table_config.default_view if table_config else "tabular",
                "layout": table_config.default_layout if table_config else "stack",
                "per_page": table_config.per_page if table_config else 20,
            }
            if table_config
            else {},
        )

        # Map list_view sort params to TableState params
        if request.query_params.get("sort"):
            state.sort_by = request.query_params.get("sort")
        if request.query_params.get("dir"):
            state.sort_order = request.query_params.get("dir")

        # Fetch data from service
        items, total = await self._fetcher.fetch_data(
            request, resource, state, source_columns
        )

        # Build columns
        columns = build_columns(source_columns, items)

        # Prepare Filters
        filter_options = get_filter_options(table_config, resource)

        # Prepare Actions
        row_actions = get_row_actions(table_config, resource, resource_prefix)

        header_actions = get_header_actions(table_config, resource)

        # Prepare Bulk Actions
        bulk_actions_list = get_bulk_actions(table_config, resource)

        # Prepare DataTable
        dt = DataTable(
            columns=columns,
            data=items,
            state=state,
            config=TableConfiguration(
                columns=columns,
                resource_name=self.resource_name,
                resource_prefix=resource_prefix,
                actions=row_actions,
                header_actions=header_actions,
                bulk_actions=bulk_actions_list,
                filter_options=filter_options,
                default_sort_by=state.sort_by,
                default_sort_order=state.sort_order,
                default_layout=table_config.default_layout if table_config else "stack",
                default_view=table_config.default_view if table_config else "tabular",
                group_by=state.group_by
                or (table_config.group_by if table_config else None),
                empty_state_title=(
                    table_config.empty_state_title if table_config else None
                ),
                empty_state_message=(
                    table_config.empty_state_message if table_config else None
                ),
                empty_state_icon=(
                    table_config.empty_state_icon if table_config else None
                ),
                search_fields=getattr(resource, "search_fields", None),
            ),
            total=total,
            user=user,
            loading=False,
        )

        is_htmx = wants_fragment(request)
        if is_htmx:
            hx_target = request.headers.get("HX-Target", "")

            # Only emit OOB control fragments for data-zone requests (search,
            # filter, paginate) where the primary swap targets #table-data and
            # toolbar elements outside the data zone need updating. Skip OOB
            # for full-zone swaps (#lexigram-table) and sidebar nav
            # (#main-content) since the primary swap replaces the entire
            # subtree, making OOB redundant.
            if hx_target == Zones.DATA.id:
                dt.props["htmx_request"] = True

            content = render_to_string(dt)
            resp_headers = {}

            # Synchronization: Force the browser URL to match the clean server-side state.
            # This removes empty params (search=&foo=) that HTMX sends via hx-include.
            # We only do this if push was not explicitly disabled in the request.
            if request.headers.get("HX-Push-Url") != "false":
                resp_headers["HX-Push-Url"] = state.to_url(resource_prefix)

            return HTMLResponse(content, headers=resp_headers)

        # Direct navigation — return full page via AdminRenderer (Jinja2 + nav population).
        return self._renderer.render_page(
            dt,
            request=request,
            title=label,
            breadcrumbs=[
                {"label": "Dashboard", "url": self._config.prefix},
                {"label": label, "url": resource_prefix},
            ],
        )


__all__ = ["ListRenderer"]
