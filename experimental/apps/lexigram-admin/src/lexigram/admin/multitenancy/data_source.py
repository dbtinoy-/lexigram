"""TenantScopedDataSource — data source wrapper that injects tenant_id into queries."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from lexigram.logging import get_logger

logger = get_logger(__name__)


class TenantScopedDataSource:
    """Wrap a data source and enforce the current tenant boundary.

    ``tenant_id`` is retained as a safe fallback for callers outside an HTTP
    request. During a request, :class:`AdminTenantMiddleware` binds the
    resolved tenant in a ``ContextVar`` so one startup-resolved data source
    remains safe under concurrent requests and tenant switching.
    """

    def __init__(
        self,
        data_source: Any,
        tenant_id: str,
        tenant_field: str = "tenant_id",
    ) -> None:
        self._ds = data_source
        self._tenant_id = tenant_id
        self._tenant_field = tenant_field

    def _effective_tenant_id(self) -> str:
        """Return the request tenant, falling back to the configured tenant."""
        from lexigram.admin.multitenancy.context import get_current_tenant

        request_tenant = get_current_tenant()
        tenant_id = self._tenant_id if request_tenant is None else request_tenant
        return str(tenant_id) if tenant_id is not None else ""

    def _inject_tenant(self, query: Any) -> Any | None:
        """Return *query* with a mandatory tenant predicate.

        QuerySpec is immutable and must be updated through its canonical
        transition method. Legacy mutable query objects are supported for
        compatibility. Unknown query shapes fail closed by returning ``None``
        instead of delegating an unscoped query.
        """
        tenant_id = self._effective_tenant_id()
        # Prefer the legacy mutable protocol when present. This also avoids
        # mistaking dynamically-created attributes on permissive test doubles
        # for an immutable QuerySpec transition method.
        add_filter = getattr(query, "add_filter", None)
        if callable(add_filter):
            # ``add_filter`` is the legacy mutable-query protocol. Some
            # implementations return themselves (and mocks return a truthy
            # sentinel), but the contract is mutation in place; preserving
            # the original object keeps downstream query identity intact.
            add_filter(self._tenant_field, "eq", tenant_id)
            return query

        with_where_eq = getattr(query, "with_where_eq", None)
        if callable(with_where_eq):
            return with_where_eq(self._tenant_field, tenant_id)

        logger.error(
            "TenantScopedDataSource cannot scope unsupported query %r",
            type(query).__name__,
        )
        return None

    def _record_tenant(self, record: Any) -> Any:
        """Extract tenant metadata without treating arbitrary mock attributes as IDs."""
        if isinstance(record, dict):
            return record.get(self._tenant_field)
        value = getattr(record, self._tenant_field, None)
        return value if isinstance(value, (str, int, UUID)) else None

    def _in_scope(self, record: Any) -> bool:
        """Return whether a concrete record belongs to the active tenant."""
        record_tenant = self._record_tenant(record)
        return record_tenant is not None and str(record_tenant) == self._effective_tenant_id()

    def _filter_result(self, result: Any) -> Any:
        """Apply a response-side tenant check to defensive read results."""
        if isinstance(result, list):
            return [record for record in result if self._in_scope(record)]

        items = getattr(result, "items", None)
        if not isinstance(items, (list, tuple)):
            return result

        safe_items = [record for record in items if self._in_scope(record)]
        from lexigram.admin.data.data_source import QueryResult

        if isinstance(result, QueryResult):
            return QueryResult(
                items=safe_items,
                total=result.total,
                page=result.page,
                per_page=result.per_page,
                has_next=result.has_next,
                has_prev=result.has_prev,
                cursor=result.cursor,
            )
        return result

    async def list(self, query: Any) -> Any:
        """List records filtered to the active tenant."""
        scoped_query = self._inject_tenant(query)
        if scoped_query is None:
            return []
        list_method = getattr(self._ds, "list", None)
        if not callable(list_method):
            find_many = getattr(self._ds, "find_many", None)
            if not callable(find_many):
                return []
            return self._filter_result(await find_many(scoped_query))
        return self._filter_result(await list_method(scoped_query))

    async def find_many(self, query: Any) -> Any:
        """Find many records through the canonical IDataSource protocol."""
        scoped_query = self._inject_tenant(query)
        if scoped_query is None:
            from lexigram.admin.data.data_source import QueryResult

            return QueryResult(items=[])
        find_many = getattr(self._ds, "find_many", None)
        if callable(find_many):
            return self._filter_result(await find_many(scoped_query))
        return await self.list(scoped_query)

    async def count(self, query: Any) -> int:
        """Count records while applying the same tenant predicate as reads."""
        scoped_query = self._inject_tenant(query)
        if scoped_query is None:
            return 0
        count_method = getattr(self._ds, "count", None)
        if callable(count_method):
            return await count_method(scoped_query)
        result = await self.find_many(query)
        return int(getattr(result, "total", len(result) if hasattr(result, "__len__") else 0))

    async def find_one(self, id: Any) -> Any:
        """Find a single record, ensuring it belongs to the active tenant."""
        record = await self._ds.find_one(id)
        if record is None:
            return None
        record_tenant = self._record_tenant(record)
        if record_tenant is None or str(record_tenant) != self._effective_tenant_id():
            logger.warning(
                "TenantScopedDataSource: tenant mismatch for id=%s (expected %s, got %s)",
                id,
                self._effective_tenant_id(),
                record_tenant,
            )
            return None
        return record

    async def _check_write_scope(self, id: Any) -> None:
        """Reject a write when the underlying source exposes a concrete other-tenant row.

        A missing row is left to the underlying source's normal not-found
        semantics. This preserves compatibility with data sources that do not
        implement ``find_one`` while still rejecting concrete cross-tenant
        records before mutation.
        """
        find_one = getattr(self._ds, "find_one", None)
        if not callable(find_one):
            return
        record = await find_one(id)
        if record is None:
            return
        record_tenant = self._record_tenant(record)
        if record_tenant is None or str(record_tenant) != self._effective_tenant_id():
            raise PermissionError(
                f"item {id!r} is missing tenant scope or belongs to another tenant"
            )

    async def create(self, data: dict[str, Any]) -> Any:
        """Create a record with the tenant field pre-populated."""
        data = {**data, self._tenant_field: self._effective_tenant_id()}
        return await self._ds.create(data)

    async def update(self, id: Any, data: dict[str, Any]) -> Any:
        """Update a record after checking its concrete tenant boundary."""
        await self._check_write_scope(id)
        if self._tenant_field in data:
            data = {**data, self._tenant_field: self._effective_tenant_id()}
        return await self._ds.update(id, data)

    async def delete(self, id: Any) -> bool:
        """Delete a record after checking its concrete tenant boundary."""
        await self._check_write_scope(id)
        return await self._ds.delete(id)

    async def bulk_create(self, items: list[dict[str, Any]]) -> list[Any]:
        """Create multiple records with the active tenant stamped on each."""
        return [await self.create(dict(item)) for item in items]

    async def bulk_update(self, ids: list[Any], data: dict[str, Any]) -> int:
        """Update only records that remain inside the active tenant."""
        count = 0
        for item_id in ids:
            try:
                await self.update(item_id, dict(data))
                count += 1
            except PermissionError:
                logger.warning("bulk_update: skipped out-of-scope id=%s", item_id)
        return count

    async def bulk_delete(self, ids: list[Any]) -> int:
        """Delete only records that remain inside the active tenant."""
        count = 0
        for item_id in ids:
            try:
                if await self.delete(item_id):
                    count += 1
            except PermissionError:
                logger.warning("bulk_delete: skipped out-of-scope id=%s", item_id)
        return count

    @property
    def tenant_id(self) -> str:
        """The active tenant identifier (or the configured fallback)."""
        return self._effective_tenant_id()


__all__ = [
    "TenantScopedDataSource",
]
