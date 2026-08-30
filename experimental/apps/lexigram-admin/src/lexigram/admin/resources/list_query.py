"""Data fetching and pagination for admin list views.

Resolves optional cache/search/resilience integrations per resource and
fetches the current page of rows through the resource's fetch_list /
find_many service patterns. Composed by
:class:`lexigram.admin.resources.list_renderer.ListRenderer`.
"""

from __future__ import annotations

import hashlib
from typing import Any

from lexigram.admin.data.query import QuerySpec
from lexigram.admin.exceptions import DataError
from lexigram.admin.observability.admin_metrics import AdminMetrics, OperationTimer
from lexigram.logging import get_logger
from lexigram.ui import TableState

logger = get_logger(__name__)


class ListDataFetcher:
    """Fetches paginated list data for a single admin resource.

    Lazily binds cache, search, and resilience integrations the first
    time the corresponding resource spec is present.
    """

    def __init__(self, resource_name: str, metrics: AdminMetrics | None = None):
        self.resource_name = resource_name
        self._metrics = metrics or AdminMetrics(None)
        self._cache_integration: Any = None
        self._search_integration: Any = None
        self._resilience_integration: Any = None
        # Set per fetch so callers can render a recoverable table error
        # instead of mistaking a failed query for a valid empty result.
        self.error: str | None = None

    async def fetch_data(
        self, request, resource, state: TableState, source_columns
    ) -> Any:
        """Fetch data from the resource service."""
        timer = OperationTimer()
        items: list[Any] = []
        total = 0
        status = "success"
        failed = False
        self.error = None

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
                elif getattr(col, "searchable", False):
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
                    items = list(result.rows or [])
                    total = result.row_count
                elif isinstance(result, dict):
                    items = list(result.get("results", []) or [])
                    total = result.get("total", len(items))
                else:
                    items, total = [], 0
                total = int(total) if total is not None else len(items)

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
                    cache_key = self._build_cache_key(request, state)
                    items, total = await self._cache_integration.get_or_compute(
                        cache_key,
                        fetcher,
                        cache_spec.ttl_seconds,
                    )
                else:
                    items, total = await fetcher()
                items = list(items or [])
                total = int(total) if total is not None else len(items)

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
                    items = list(
                        (result.items if hasattr(result, "items") else result) or []
                    )
                    total = result.total if hasattr(result, "total") else len(items)
                    total = int(total) if total is not None else len(items)
                elif hasattr(service, "list"):
                    items = list(
                        await service.list(
                            limit=state.per_page,
                            offset=(state.page - 1) * state.per_page,
                        )
                        or []
                    )
                    total = len(items)
        except DataError as e:
            logger.error(
                "Failed to list items for %s: %s",
                self.resource_name,
                e,
                exc_info=True,
            )
            self.error = f"Failed to retrieve {self.resource_name} items"
            failed = True
        except Exception:  # noqa: BLE001
            logger.exception("admin.resource_fetch_error", resource=self.resource_name)
            self.error = f"Failed to retrieve {self.resource_name} items"
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

    def _build_cache_key(self, request: Any, state: TableState) -> str:
        """Build a cache key that cannot cross tenant/user/table state boundaries.

        A list response can vary by tenant, principal permissions, filters,
        search, pagination, sort, or soft-delete scope. The former key only
        used page and sort, which could serve another tenant's or another
        user's response when caching was enabled. Keep the structured state
        out of the backend key itself and hash it to avoid leaking query data
        into cache instrumentation/logs.
        """
        request_state = getattr(request, "state", None)
        tenant_id = getattr(request_state, "tenant_id", None)
        if not tenant_id:
            from lexigram.admin.multitenancy.context import get_current_tenant

            tenant_id = get_current_tenant()
        tenant_id = tenant_id or "__unresolved__"
        user = getattr(request_state, "user", None)
        if user is None:
            request_scope = getattr(request, "scope", None)
            user = (
                request_scope.get("user")
                if isinstance(request_scope, dict)
                else None
            )
        principal = (
            getattr(user, "id", None)
            or getattr(user, "user_id", None)
            or getattr(user, "email", None)
            or ("anonymous" if user is None else str(user))
        )
        permissions = getattr(request_state, "permissions", None)
        if permissions is None:
            permissions = getattr(user, "permissions", None)
        if isinstance(permissions, dict):
            permissions = sorted(
                (str(key), str(value)) for key, value in permissions.items()
            )
        elif permissions is not None:
            try:
                permissions = sorted(str(value) for value in permissions)
            except TypeError:
                # A service object is not a principal permission set; the
                # principal identifier above still prevents cross-user reuse.
                permissions = type(permissions).__qualname__

        payload = {
            "tenant": str(tenant_id),
            "principal": str(principal),
            "permissions": permissions,
            "page": state.page,
            "per_page": state.per_page,
            "cursor": state.cursor,
            "sort_by": state.sort_by,
            "sort_order": state.sort_order,
            "search": state.search,
            "filters": state.filters,
            "group_by": state.group_by,
            "include_deleted": state.include_deleted,
        }
        from lexigram.serialization import dumps_str

        serialized = dumps_str(payload, sort_keys=True)
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return self._cache_integration.cache_key(self.resource_name, digest)

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


__all__ = ["ListDataFetcher"]
