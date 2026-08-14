from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.data.data_source import QueryResult
from lexigram.admin.integrations.search_sync import SearchSyncDataSourceWrapper
from lexigram.contracts.search import SearchableSpec


class _FakeSearchEngine:
    """Minimal fake that matches the SearchEngine protocol."""

    def __init__(self) -> None:
        self.index = AsyncMock(return_value=True)
        self.delete = AsyncMock(return_value=True)


class _InnerDataSource:
    """A simple test double that implements IDataSource."""

    def __init__(self) -> None:
        self._created: list = []
        self._updated: list = []
        self._deleted: list = []

    async def find_one(self, item_id):
        return None

    async def find_many(self, query):
        return QueryResult(items=[], total=0)

    async def count(self, query):
        return 0

    async def create(self, data):
        entity = {**data, "id": 123}
        self._created.append(entity)
        return entity

    async def update(self, item_id, data):
        entity = {**data, "id": item_id}
        self._updated.append(entity)
        return entity

    async def delete(self, item_id):
        self._deleted.append(item_id)
        return True

    async def bulk_create(self, items):
        return items

    async def bulk_update(self, ids, data):
        return len(ids)

    async def bulk_delete(self, ids):
        return len(ids)


@pytest.fixture
def search_engine():
    return _FakeSearchEngine()


@pytest.fixture
def spec():
    return SearchableSpec(index_name="test_idx", fields=("name", "email"))


@pytest.fixture
def inner():
    return _InnerDataSource()


@pytest.fixture
def wrapper(inner, search_engine, spec):
    return SearchSyncDataSourceWrapper(inner, search_engine, spec)


class TestSearchSyncDataSourceWrapper:
    """SearchSyncDataSourceWrapper must proxy all IDataSource methods
    and sync create/update/delete to the search engine."""

    async def test_create_proxies_and_indexes(self, wrapper, search_engine, inner):
        result = await wrapper.create({"name": "Alice", "email": "a@b.com"})
        assert result == {"name": "Alice", "email": "a@b.com", "id": 123}
        assert inner._created == [result]
        search_engine.index.assert_awaited_once_with(
            "test_idx",
            [{"name": "Alice", "email": "a@b.com", "id": "123"}],
        )

    async def test_update_proxies_and_indexes(self, wrapper, search_engine, inner):
        result = await wrapper.update(42, {"name": "Bob"})
        assert result == {"name": "Bob", "id": 42}
        assert inner._updated == [result]
        search_engine.index.assert_awaited_once_with(
            "test_idx",
            [{"name": "Bob", "email": None, "id": "42"}],
        )

    async def test_delete_proxies_and_removes(self, wrapper, search_engine, inner):
        ok = await wrapper.delete(99)
        assert ok is True
        assert inner._deleted == [99]
        search_engine.delete.assert_awaited_once_with(
            "test_idx", "99",
        )

    async def test_delete_skips_remove_when_inner_fails(self, wrapper, search_engine, inner):
        inner.delete = AsyncMock(return_value=False)
        ok = await wrapper.delete(99)
        assert ok is False
        search_engine.delete.assert_not_called()

    async def test_find_one_delegates(self, wrapper, inner):
        inner.find_one = AsyncMock(return_value="found")
        result = await wrapper.find_one(1)
        assert result == "found"

    async def test_find_many_delegates(self, wrapper, inner):
        qr = QueryResult(items=[], total=0)
        inner.find_many = AsyncMock(return_value=qr)
        result = await wrapper.find_many(MagicMock())
        assert result is qr

    async def test_count_delegates(self, wrapper, inner):
        inner.count = AsyncMock(return_value=7)
        result = await wrapper.count(MagicMock())
        assert result == 7

    async def test_bulk_create_delegates(self, wrapper, inner):
        inner.bulk_create = AsyncMock(return_value=[{"id": 1}])
        result = await wrapper.bulk_create([{"name": "X"}])
        assert result == [{"id": 1}]

    async def test_bulk_update_delegates(self, wrapper, inner):
        inner.bulk_update = AsyncMock(return_value=3)
        result = await wrapper.bulk_update([1, 2, 3], {"active": True})
        assert result == 3

    async def test_bulk_delete_delegates(self, wrapper, inner):
        inner.bulk_delete = AsyncMock(return_value=2)
        result = await wrapper.bulk_delete([1, 2])
        assert result == 2

    async def test_search_engine_error_does_not_propagate(self, wrapper, search_engine, inner):
        search_engine.index.side_effect = RuntimeError("search down")
        result = await wrapper.create({"name": "X"})
        assert result is not None  # create still succeeds

    async def test_no_index_name_skips(self, inner, search_engine):
        spec = SearchableSpec(index_name=None, fields=("name",))
        wrapper = SearchSyncDataSourceWrapper(inner, search_engine, spec)
        result = await wrapper.create({"name": "X"})
        search_engine.index.assert_not_called()

    async def test_model_object_extracts_attrs(self, wrapper, search_engine, inner):
        class Model:
            id = 77
            name = "Model"
            email = "m@m.com"
        inner.create = AsyncMock(return_value=Model())
        result = await wrapper.create({"name": "M"})
        assert result.id == 77
        search_engine.index.assert_awaited_once_with(
            "test_idx",
            [{"name": "Model", "email": "m@m.com", "id": "77"}],
        )
