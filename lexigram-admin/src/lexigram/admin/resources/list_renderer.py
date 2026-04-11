from __future__ import annotations

"""List view rendering for admin resources."""

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.admin.config import AdminConfig
from lexigram.admin.data.query import QuerySpec
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.exceptions import DataError
from lexigram.admin.observability.admin_metrics import AdminMetrics, OperationTimer
from lexigram.admin.resources.config import TableConfiguration
from lexigram.admin.ui.columns import Column as OrgColumn
from lexigram.admin.ui.columns import TextColumn
from lexigram.admin.ui.organisms.data_table import DataTable
from lexigram.admin.ui.state import TableState
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.ui import Zones, render_to_string

logger = get_logger(__name__)


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
        self._cache_integration: Any = None
        self._search_integration: Any = None
        self._resilience_integration: Any = None

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
        items, total = await self._fetch_data(request, resource, state, source_columns)

        # Build columns
        columns = self._build_columns(source_columns, items)

        # Prepare Filters
        filter_options = self._get_filter_options(table_config, resource)

        # Prepare Actions
        row_actions = self._get_row_actions(table_config, resource, resource_prefix)

        header_actions = self._get_header_actions(table_config, resource)

        # Prepare Bulk Actions
        bulk_actions_list = self._get_bulk_actions(table_config, resource)

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
                search_fields=getattr(resource, "search_fields", None),
            ),
            total=total,
            user=user,
            loading=False,
        )

        is_htmx = "HX-Request" in request.headers
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

    async def _fetch_data(
        self, request, resource, state: TableState, source_columns
    ) -> Any:
        """Fetch data from the resource service."""
        timer = OperationTimer()
        items: list[Any] = []
        total = 0
        status = "success"
        failed = False

        if not resource:
            self._metrics.record_operation(
                "list",
                resource=self.resource_name,
                status=status,
                duration_seconds=timer.elapsed(),
            )
            return items, total

        # Use resource search_fields when available, otherwise derive from columns
        resource_search_fields: list[str] | None = getattr(
            resource, "search_fields", None
        )
        if resource_search_fields:
            search_fields = list(resource_search_fields)
        else:
            search_fields = []
            for col in source_columns:
                if hasattr(col, "is_searchable") and col.is_searchable():
                    search_fields.append(col.name)

        # Extract active filters from TableState
        filters: dict[str, Any] = dict(state.filters) if state.filters else {}

        try:
            # Check if this resource should be cached
            cache_spec = self._resolve_cache_spec(resource)

            # Check if search integration should be used
            search_spec = self._resolve_search_spec(resource)

            # Check if resilience integration should be used
            resilient_spec = self._resolve_resilient_spec(resource)

            # Search path: when a search query is active and a search spec exists,
            # route through the search integration instead of the LIKE-based query
            if state.search and search_spec and self._search_integration:
                index = search_spec.index_name or self.resource_name
                result = await self._search_integration.query(
                    index=index,
                    query_str=state.search,
                    limit=state.per_page,
                    offset=(state.page - 1) * state.per_page,
                )
                if hasattr(result, "rows"):
                    items = list(result.rows)
                    total = result.row_count
                elif isinstance(result, dict):
                    items = list(result.get("results", []))
                    total = result.get("total", len(items))
                else:
                    items, total = [], 0

                # If search returned results, return them.
                # Otherwise fall through to fetch_list when fallback_to_like is enabled
                # so that the SearchQueryDataSourceWrapper can try a LIKE query.
                if items or not self._search_integration.fallback_to_like:
                    status = "success"
                    self._metrics.record_operation(
                        "list",
                        resource=self.resource_name,
                        status=status,
                        duration_seconds=timer.elapsed(),
                    )
                    return items, total

                logger.info(
                    "search_integration_fallback",
                    resource=self.resource_name,
                    query=state.search,
                )

            # Primary path: resource.fetch_list() — handles all service patterns
            if hasattr(resource, "fetch_list"):
                fetch_kwargs = {
                    "limit": state.per_page,
                    "offset": (state.page - 1) * state.per_page,
                    "filters": filters,
                    "search": state.search or None,
                    "search_fields": search_fields or None,
                    "sort_by": state.sort_by or None,
                    "sort_order": state.sort_order or "asc",
                    "include_deleted": state.include_deleted,
                }

                # Build the fetch callable, optionally wrapped with resilience
                if resilient_spec and self._resilience_integration:

                    async def _resilient_fetch() -> tuple[list[Any], int]:
                        return await self._resilience_integration.execute(
                            resource.fetch_list,
                            **fetch_kwargs,
                        )

                    fetcher = _resilient_fetch
                else:

                    async def _fetch() -> tuple[list[Any], int]:
                        return await resource.fetch_list(**fetch_kwargs)

                    fetcher = _fetch

                if cache_spec and self._cache_integration:
                    cache_key = self._cache_integration.cache_key(
                        self.resource_name,
                        str(state.page),
                        state.sort_by or "",
                    )
                    items, total = await self._cache_integration.get_or_compute(
                        cache_key,
                        fetcher,
                        cache_spec.ttl_seconds,
                    )
                else:
                    items, total = await fetcher()

                logger.info(
                    "search.fetch_list_result",
                    resource=self.resource_name,
                    search=state.search,
                    search_fields=search_fields,
                    item_count=len(items),
                    total=total,
                )

            # Legacy fallback: direct service.find_many(query)
            elif hasattr(resource, "service") and resource.service:
                service = resource.service
                if hasattr(service, "find_many"):
                    qs = QuerySpec()
                    if state.search and search_fields:
                        qs = qs.with_search(state.search, search_fields)
                    if state.page and state.per_page:
                        qs = qs.with_page(state.page).with_per_page(state.per_page)
                    if state.sort_by:
                        qs = qs.with_order_by(state.sort_by, state.sort_order)
                    if state.include_deleted:
                        qs = qs.with_deleted(True)
                    for field, value in filters.items():
                        if isinstance(value, list):
                            qs = qs.with_where_in(field, list(value))
                        else:
                            qs = qs.with_where_eq(field, value)
                    result = await service.find_many(qs)
                    items = result.items if hasattr(result, "items") else result
                    total = result.total if hasattr(result, "total") else len(items)
                elif hasattr(service, "list"):
                    items = await service.list(
                        limit=state.per_page,
                        offset=(state.page - 1) * state.per_page,
                    )
                    total = len(items)
        except DataError as e:
            logger.error(
                "Failed to list items for %s: %s",
                self.resource_name,
                e,
                exc_info=True,
            )
            raise DataError(
                message=f"Failed to retrieve {self.resource_name} items",
                original_error=e,
            ) from None
        except Exception:  # noqa: BLE001
            logger.exception("admin.resource_fetch_error", resource=self.resource_name)
            failed = True

        if failed:
            status = "error"

        logger.info(
            "search.fetch_data_result",
            resource=self.resource_name,
            search=state.search,
            item_count=len(items),
            total=total,
            status=status,
            failed=failed,
        )

        self._metrics.record_operation(
            "list",
            resource=self.resource_name,
            status=status,
            duration_seconds=timer.elapsed(),
        )
        return items, total

    def _resolve_cache_spec(self, resource: Any) -> Any:
        """Return a CacheableSpec if resource is cacheable, else None."""
        if not resource:
            return None
        spec_fn = getattr(resource, "cache_spec", None)
        if not spec_fn:
            return None
        spec = spec_fn()
        if not spec:
            return None
        from lexigram.admin.integrations import get as get_integration

        self._cache_integration = get_integration("CacheIntegration")
        return spec if self._cache_integration else None

    def _resolve_search_spec(self, resource: Any) -> Any:
        """Return a SearchableSpec if resource is searchable, else None."""
        if not resource:
            return None
        spec_fn = getattr(resource, "search_spec", None)
        if not spec_fn:
            return None
        spec = spec_fn()
        if not spec:
            return None
        from lexigram.admin.integrations import get as get_integration

        self._search_integration = get_integration("SearchIntegration")
        return spec if self._search_integration else None

    def _resolve_resilient_spec(self, resource: Any) -> Any:
        """Return a ResilientSpec if resource is resilient, else None."""
        if not resource:
            return None
        spec_fn = getattr(resource, "resilient_spec", None)
        if not spec_fn:
            return None
        spec = spec_fn()
        if not spec:
            return None
        from lexigram.admin.integrations import get as get_integration

        self._resilience_integration = get_integration("ResilienceIntegration")
        return spec if self._resilience_integration else None

    def _build_columns(self, source_columns, items) -> Any:
        """Build column definitions for the data table."""
        columns = []
        # Auto-generate columns if missing (post-fetch)
        if not source_columns and items:
            first_item = items[0]
            item_dict = (
                first_item.model_dump()
                if hasattr(first_item, "model_dump")
                else (
                    dict(first_item)
                    if not isinstance(first_item, (str, int, float))
                    else {"id": first_item}
                )
            )
            for key in list(item_dict.keys())[:6]:
                columns.append(
                    TextColumn(name=key, label=key.replace("_", " ").title()),
                )
        else:
            # Convert or preserve columns
            for col in source_columns:
                if hasattr(col, "render") or isinstance(col, OrgColumn):
                    # Already a component
                    columns.append(col)
                else:
                    # Fallback for simple objects
                    new_col = TextColumn(
                        name=getattr(col, "name", str(col)),
                        label=getattr(
                            col,
                            "label",
                            getattr(col, "name", str(col)).replace("_", " ").title(),
                        ),
                    ).sortable(True)
                    columns.append(new_col)

        return columns

    def _get_filter_options(self, table_config, resource) -> Any:
        """Get filter options from resource configuration."""
        filter_options = []
        if table_config and table_config.filter_options:
            filter_options = table_config.filter_options
        elif resource and hasattr(resource, "filter_options"):
            filter_options = (
                resource.filter_options
                if not callable(resource.filter_options)
                else resource.filter_options()
            )
        elif resource and hasattr(resource, "filters"):
            filter_options = (
                resource.filters
                if not callable(resource.filters)
                else resource.filters()
            )
        return filter_options

    def _get_row_actions(self, table_config, resource, resource_prefix) -> Any:
        """Get row actions from resource configuration."""
        row_actions = []
        if table_config and table_config.actions:
            row_actions = table_config.actions
        elif resource and hasattr(resource, "actions"):
            actions = (
                resource.actions
                if not callable(resource.actions)
                else resource.actions()
            )
            row_actions = list(actions)

        # Inject default URLs for standard actions if missing
        from lexigram.admin.ui.actions.standard import EditAction, ViewAction

        for action in row_actions:
            if (
                isinstance(action, (EditAction, ViewAction))
                and not action.get_url()
                and not action.get_hx_get()
            ):
                # Default logic: {prefix}/{id}/edit or {prefix}/{id}
                postfix = "/edit" if isinstance(action, EditAction) else ""

                # Use hx_get for partial updates (SlideOver/Modal)
                action.hx(get=f"{resource_prefix.rstrip('/')}/{{id}}{postfix}")

        return row_actions

    def _get_header_actions(self, table_config, resource) -> Any:
        """Get header actions from resource configuration."""
        header_actions = []
        if (
            table_config
            and hasattr(table_config, "header_actions")
            and table_config.header_actions
        ):
            header_actions = table_config.header_actions
        elif resource and hasattr(resource, "header_actions"):
            header_actions = (
                resource.header_actions
                if not callable(resource.header_actions)
                else resource.header_actions()
            )
        return header_actions

    def _get_bulk_actions(self, table_config, resource) -> Any:
        """Get bulk actions from resource configuration."""
        bulk_actions_list = []
        source_bulk = []
        if table_config and table_config.bulk_actions:
            source_bulk = table_config.bulk_actions
        elif resource and hasattr(resource, "bulk_actions"):
            source_bulk = (
                resource.bulk_actions
                if not callable(resource.bulk_actions)
                else resource.bulk_actions()
            )

        from lexigram.admin.ui.actions.standard import BulkAction as OrgBulkAction
        from lexigram.admin.ui.actions.standard import DeleteBulkAction

        for ba in source_bulk:
            if isinstance(ba, OrgBulkAction):
                bulk_actions_list.append(ba)
            elif ba == "delete_selected":
                bulk_actions_list.append(DeleteBulkAction(label="Delete Selected"))
            elif isinstance(ba, str):
                # Generic bulk action from string
                bulk_actions_list.append(
                    OrgBulkAction(label=ba.replace("_", " ").title(), name=ba),
                )

        return bulk_actions_list


__all__ = ["ListRenderer"]
