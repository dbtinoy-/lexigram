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

    def __init__(self, repository: AdminRepositoryProtocol[T]) -> None:
        self._repo = repository

    async def find_one(self, item_id: Any) -> T | None:
        return await self._repo.find_by_id(item_id)

    async def find_many(self, query: QuerySpec) -> QueryResult[T]:
        sort_field, sort_order = query.resolved_sort
        filters = query.to_repository_filters()

        items = await self._repo.find_many(
            offset=query.offset,
            limit=query.per_page,
            order_by=[(sort_field, sort_order)] if sort_field else None,
            filters=filters,
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
            filters=query.to_repository_filters(),
            search=query.search or None,
            search_fields=query.search_fields or None,
        )

    async def create(self, data: dict[str, Any]) -> T:
        return await self._repo.create(data)

    async def update(self, item_id: Any, data: dict[str, Any]) -> T:
        return await self._repo.update(item_id, data)

    async def delete(self, item_id: Any) -> bool:
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
