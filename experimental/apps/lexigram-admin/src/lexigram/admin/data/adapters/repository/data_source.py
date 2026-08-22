"""AdminRepositoryProtocol-backed IDataSource adapter."""

from __future__ import annotations

from typing import Any, Generic

from lexigram.admin.data.adapters.repository.types import T
from lexigram.admin.data.data_source import IDataSource, QueryResult
from lexigram.admin.data.query import QuerySpec
from lexigram.contracts.admin.repository import AdminRepositoryProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)


@inject
class RepositoryDataSource(IDataSource[T], Generic[T]):
    """IDataSource adapter for AdminRepositoryProtocol repositories.

    Translates QuerySpec into AdminRepositoryProtocol calls using
    QuerySpec.resolved_sort and QuerySpec.to_repository_filters().
    """

    def __init__(
        self,
        repository: AdminRepositoryProtocol[T],
        *,
        tenant_scope: str | None = None,
    ) -> None:
        self._repo = repository
        # When set, every operation is constrained to this tenant: reads get a
        # mandatory ``tenant_id`` filter / post-fetch check, writes stamp or
        # refuse. See spec-security-remediation finding 3.
        self.tenant_scope = tenant_scope

    def _scoped(self, filters: dict[str, Any] | None) -> dict[str, Any]:
        merged = dict(filters) if filters else {}
        if self.tenant_scope is not None:
            merged["tenant_id"] = self.tenant_scope
        return merged

    def _in_scope(self, item: Any) -> bool:
        if self.tenant_scope is None:
            return True
        return str(getattr(item, "tenant_id", "")) == self.tenant_scope

    async def find_one(self, item_id: Any) -> T | None:
        item = await self._repo.find_by_id(item_id)
        if item is not None and not self._in_scope(item):
            return None
        return item

    async def find_many(self, query: QuerySpec) -> QueryResult[T]:
        sort_field, sort_order = query.resolved_sort
        filters = self._scoped(query.to_repository_filters())

        items = await self._repo.find_many(
            offset=query.offset,
            limit=query.per_page,
            order_by=[(sort_field, sort_order)] if sort_field else None,
            filters=filters or None,
            search=query.search or None,
            search_fields=query.search_fields or None,
            load=query.include or None,
        )

        total = await self.count(query)

        return QueryResult(
            items=items,
            total=total,
            page=query.page,
            per_page=query.per_page,
            has_next=(query.offset + query.per_page) < total,
            has_prev=query.page > 1,
        )

    async def count(self, query: QuerySpec) -> int:
        return await self._repo.count(
            filters=self._scoped(query.to_repository_filters()),
            search=query.search or None,
            search_fields=query.search_fields or None,
        )

    async def create(self, data: dict[str, Any]) -> T:
        if self.tenant_scope is not None:
            data = {**data, "tenant_id": self.tenant_scope}
        return await self._repo.create(data)

    async def update(self, item_id: Any, data: dict[str, Any]) -> T:
        if self.tenant_scope is not None:
            existing = await self._repo.find_by_id(item_id)
            if existing is not None and not self._in_scope(existing):
                raise PermissionError(f"item {item_id!r} belongs to another tenant")
        return await self._repo.update(item_id, data)

    async def delete(self, item_id: Any) -> bool:
        if self.tenant_scope is not None:
            existing = await self._repo.find_by_id(item_id)
            if existing is not None and not self._in_scope(existing):
                raise PermissionError(f"item {item_id!r} belongs to another tenant")
        return await self._repo.delete(item_id)

    async def bulk_create(self, items: list[dict[str, Any]]) -> list[T]:
        return [await self._repo.create(item) for item in items]

    async def bulk_update(self, ids: list[Any], data: dict[str, Any]) -> int:
        count = 0
        for item_id in ids:
            try:
                await self._repo.update(item_id, data)
                count += 1
            except Exception:
                logger.warning("bulk_update: skipped id=%s", item_id)
        return count

    async def bulk_delete(self, ids: list[Any]) -> int:
        count = 0
        for item_id in ids:
            if await self._repo.delete(item_id):
                count += 1
        return count
