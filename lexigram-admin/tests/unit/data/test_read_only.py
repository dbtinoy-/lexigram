"""Tests for ReadOnlyDataSource mixin."""
from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.data.data_source import QueryResult
from lexigram.admin.data.query import QuerySpec
from lexigram.admin.data.read_only import ReadOnlyDataSource, ReadOnlyError


class _FakeReadOnlyDS(ReadOnlyDataSource[dict[str, Any]]):
    async def find_one(self, item_id: Any) -> dict[str, Any] | None:
        return {"id": item_id}

    async def find_many(self, query: QuerySpec) -> QueryResult[dict[str, Any]]:
        return QueryResult(items=[], total=0, page=1, per_page=20)

    async def count(self, query: QuerySpec) -> int:
        return 0


class TestReadOnlyDataSource:
    def setup_method(self) -> None:
        self.ds = _FakeReadOnlyDS()

    async def test_find_one_works(self) -> None:
        result = await self.ds.find_one("abc")
        assert result == {"id": "abc"}

    async def test_find_many_works(self) -> None:
        result = await self.ds.find_many(QuerySpec())
        assert result.total == 0

    async def test_count_works(self) -> None:
        assert await self.ds.count(QuerySpec()) == 0

    async def test_create_raises(self) -> None:
        with pytest.raises(ReadOnlyError):
            await self.ds.create({"name": "test"})

    async def test_update_raises(self) -> None:
        with pytest.raises(ReadOnlyError):
            await self.ds.update("abc", {"name": "test"})

    async def test_delete_raises(self) -> None:
        with pytest.raises(ReadOnlyError):
            await self.ds.delete("abc")

    async def test_bulk_create_raises(self) -> None:
        with pytest.raises(ReadOnlyError):
            await self.ds.bulk_create([{"name": "test"}])

    async def test_bulk_update_raises(self) -> None:
        with pytest.raises(ReadOnlyError):
            await self.ds.bulk_update(["abc"], {"name": "test"})

    async def test_bulk_delete_raises(self) -> None:
        with pytest.raises(ReadOnlyError):
            await self.ds.bulk_delete(["abc"])

    async def test_error_message_includes_class_name(self) -> None:
        with pytest.raises(ReadOnlyError, match="_FakeReadOnlyDS"):
            await self.ds.create({})
