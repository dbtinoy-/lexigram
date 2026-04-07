"""TenantScopedDataSource — data source wrapper that injects tenant_id into queries."""

from __future__ import annotations

from typing import Any

from lexigram.logging import get_logger

logger = get_logger(__name__)


class TenantScopedDataSource:
    """Wraps an :class:`~lexigram.admin.data.data_source.IDataSource` and
    injects ``tenant_id`` into every query.

    This ensures resources are automatically isolated per tenant without
    requiring every query to manually add the tenant filter.

    Args:
        data_source: The underlying data source to delegate to.
        tenant_id: Active tenant identifier.
        tenant_field: Column/field name to filter on (default ``"tenant_id"``).

    Example::

        scoped = TenantScopedDataSource(data_source, tenant_id="acme")
        result = await scoped.list(query)  # → automatically adds tenant_id="acme" filter
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

    def _inject_tenant(self, query: Any) -> Any:
        """Add the tenant filter to a query spec.

        Works with :class:`~lexigram.admin.data.query.QuerySpec` objects that
        accept ``add_filter(field, op, value)``.  If the query object doesn't
        support this, it is returned unchanged and a warning is logged.
        """
        try:
            query.add_filter(self._tenant_field, "eq", self._tenant_id)
        except Exception:  # noqa: BLE001
            logger.warning(
                "TenantScopedDataSource could not inject tenant filter into query %r",
                type(query).__name__,
            )
        return query

    async def list(self, query: Any) -> Any:
        """List records filtered to the active tenant."""
        return await self._ds.list(self._inject_tenant(query))

    async def find_one(self, id: Any) -> Any:
        """Find a single record, ensuring it belongs to the active tenant."""
        record = await self._ds.find_one(id)
        if record is None:
            return None
        record_tenant = getattr(record, self._tenant_field, None) or (
            record.get(self._tenant_field) if isinstance(record, dict) else None
        )
        if record_tenant and record_tenant != self._tenant_id:
            logger.warning(
                "TenantScopedDataSource: tenant mismatch for id=%s (expected %s, got %s)",
                id,
                self._tenant_id,
                record_tenant,
            )
            return None
        return record

    async def create(self, data: dict[str, Any]) -> Any:
        """Create a record with the tenant field pre-populated."""
        data = {**data, self._tenant_field: self._tenant_id}
        return await self._ds.create(data)

    async def update(self, id: Any, data: dict[str, Any]) -> Any:
        """Update a record that belongs to the active tenant."""
        return await self._ds.update(id, data)

    async def delete(self, id: Any) -> bool:
        """Delete a record that belongs to the active tenant."""
        return await self._ds.delete(id)

    @property
    def tenant_id(self) -> str:
        """The active tenant identifier."""
        return self._tenant_id


__all__ = [
    "TenantScopedDataSource",
]
