"""Read-only data source mixin for lexigram-admin."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from lexigram.admin.data.data_source import QueryResult
from lexigram.admin.data.query import QuerySpec

T = TypeVar("T")


class ReadOnlyError(Exception):
    """Raised when a write is attempted on a read-only data source."""


class ReadOnlyDataSource(ABC, Generic[T]):
    """ABC for data sources that support reads only.

    Subclasses implement find_one, find_many, count.
    All write methods raise ReadOnlyError.
    """

    @abstractmethod
    async def find_one(self, item_id: Any) -> T | None: ...

    @abstractmethod
    async def find_many(self, query: QuerySpec) -> QueryResult[T]: ...

    @abstractmethod
    async def count(self, query: QuerySpec) -> int: ...

    def _read_only(self) -> ReadOnlyError:
        return ReadOnlyError(f"{type(self).__name__} is read-only")

    async def create(self, data: dict[str, Any]) -> T:
        raise self._read_only()

    async def update(self, item_id: Any, data: dict[str, Any]) -> T:
        raise self._read_only()

    async def delete(self, item_id: Any) -> bool:
        raise self._read_only()

    async def bulk_create(self, items: list[dict[str, Any]]) -> list[T]:
        raise self._read_only()

    async def bulk_update(self, ids: list[Any], data: dict[str, Any]) -> int:
        raise self._read_only()

    async def bulk_delete(self, ids: list[Any]) -> int:
        raise self._read_only()
