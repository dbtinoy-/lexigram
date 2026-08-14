"""Tests for RepositoryDataSource — the IDataSource adapter for AdminRepositoryProtocol."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.data.adapters.repository import RepositoryDataSource
from lexigram.admin.data.data_source import IDataSource, QueryResult
from lexigram.admin.data.query import QuerySpec


def _make_repo(**overrides: Any) -> MagicMock:
    """Return a mock conforming to AdminRepositoryProtocol."""
    repo = MagicMock()
    repo.find_by_id = AsyncMock(return_value=None)
    repo.find_many = AsyncMock(return_value=[])
    repo.count = AsyncMock(return_value=0)
    repo.create = AsyncMock(side_effect=lambda data: {**data, "id": "new"})
    repo.update = AsyncMock(side_effect=lambda item_id, data: {**data, "id": item_id})
    repo.delete = AsyncMock(return_value=True)
    for attr, val in overrides.items():
        setattr(repo, attr, val)
    return repo


class TestRepositoryDataSourceIsIDataSource:
    def test_isinstance_check(self) -> None:
        ds = RepositoryDataSource(repository=_make_repo())
        assert isinstance(ds, IDataSource)


class TestRepositoryDataSourceFindOne:
    async def test_delegates_to_find_by_id(self) -> None:
        repo = _make_repo(find_by_id=AsyncMock(return_value={"id": "42", "name": "Cat"}))
        ds = RepositoryDataSource(repository=repo)
        result = await ds.find_one("42")
        repo.find_by_id.assert_awaited_once_with("42")
        assert result == {"id": "42", "name": "Cat"}

    async def test_returns_none_when_not_found(self) -> None:
        ds = RepositoryDataSource(repository=_make_repo())
        assert await ds.find_one("missing") is None


class TestRepositoryDataSourceFindMany:
    async def test_uses_resolved_sort(self) -> None:
        """A sort_by with '-' prefix is decoded to desc."""
        repo = _make_repo(count=AsyncMock(return_value=0))
        ds = RepositoryDataSource(repository=repo)
        query = QuerySpec(sort_by="-created_at", per_page=10)
        await ds.find_many(query)
        call_kwargs = repo.find_many.call_args.kwargs
        assert call_kwargs["order_by"] == [("created_at", "desc")]

    async def test_no_order_by_when_no_sort(self) -> None:
        repo = _make_repo(count=AsyncMock(return_value=0))
        ds = RepositoryDataSource(repository=repo)
        await ds.find_many(QuerySpec())
        assert repo.find_many.call_args.kwargs["order_by"] is None

    async def test_passes_filters(self) -> None:
        repo = _make_repo(count=AsyncMock(return_value=0))
        ds = RepositoryDataSource(repository=repo)
        query = QuerySpec(filters={"status": "active"})
        await ds.find_many(query)
        assert repo.find_many.call_args.kwargs["filters"] == {"status": "active"}

    async def test_no_filters_passes_none(self) -> None:
        repo = _make_repo(count=AsyncMock(return_value=0))
        ds = RepositoryDataSource(repository=repo)
        await ds.find_many(QuerySpec())
        assert repo.find_many.call_args.kwargs["filters"] is None

    async def test_passes_search_and_fields(self) -> None:
        repo = _make_repo(count=AsyncMock(return_value=0))
        ds = RepositoryDataSource(repository=repo)
        query = QuerySpec(search="fluffy", search_fields=["name"])
        await ds.find_many(query)
        kw = repo.find_many.call_args.kwargs
        assert kw["search"] == "fluffy"
        assert kw["search_fields"] == ["name"]

    async def test_pagination_offset_and_limit(self) -> None:
        repo = _make_repo(count=AsyncMock(return_value=100))
        ds = RepositoryDataSource(repository=repo)
        query = QuerySpec(page=3, per_page=10)
        result = await ds.find_many(query)
        kw = repo.find_many.call_args.kwargs
        assert kw["offset"] == 20
        assert kw["limit"] == 10
        assert result.page == 3
        assert result.per_page == 10

    async def test_has_next_and_prev(self) -> None:
        repo = _make_repo(
            find_many=AsyncMock(return_value=[{"id": str(i)} for i in range(10)]),
            count=AsyncMock(return_value=100),
        )
        ds = RepositoryDataSource(repository=repo)
        result = await ds.find_many(QuerySpec(page=2, per_page=10))
        assert result.has_next is True
        assert result.has_prev is True

    async def test_returns_query_result(self) -> None:
        items = [{"id": "1"}, {"id": "2"}]
        repo = _make_repo(
            find_many=AsyncMock(return_value=items),
            count=AsyncMock(return_value=2),
        )
        ds = RepositoryDataSource(repository=repo)
        result = await ds.find_many(QuerySpec())
        assert isinstance(result, QueryResult)
        assert result.items == items
        assert result.total == 2


class TestRepositoryDataSourceCount:
    async def test_delegates_with_filters_and_search(self) -> None:
        repo = _make_repo(count=AsyncMock(return_value=42))
        ds = RepositoryDataSource(repository=repo)
        query = QuerySpec(filters={"plan": "pro"}, search="alice", search_fields=["email"])
        count = await ds.count(query)
        repo.count.assert_awaited_once_with(
            filters={"plan": "pro"},
            search="alice",
            search_fields=["email"],
        )
        assert count == 42


class TestRepositoryDataSourceCreate:
    async def test_delegates_to_repo(self) -> None:
        repo = _make_repo()
        ds = RepositoryDataSource(repository=repo)
        result = await ds.create({"name": "Luna"})
        repo.create.assert_awaited_once_with({"name": "Luna"})
        assert result["name"] == "Luna"


class TestRepositoryDataSourceUpdate:
    async def test_delegates_item_id_and_data(self) -> None:
        repo = _make_repo()
        ds = RepositoryDataSource(repository=repo)
        result = await ds.update("99", {"name": "Luna"})
        repo.update.assert_awaited_once_with("99", {"name": "Luna"})
        assert result["id"] == "99"


class TestRepositoryDataSourceDelete:
    async def test_returns_true_on_success(self) -> None:
        repo = _make_repo(delete=AsyncMock(return_value=True))
        ds = RepositoryDataSource(repository=repo)
        assert await ds.delete("42") is True

    async def test_returns_false_when_not_found(self) -> None:
        repo = _make_repo(delete=AsyncMock(return_value=False))
        ds = RepositoryDataSource(repository=repo)
        assert await ds.delete("missing") is False


class TestRepositoryDataSourceBulkOps:
    async def test_bulk_create(self) -> None:
        created = []
        async def _create(data: dict[str, Any]) -> dict[str, Any]:
            created.append(data)
            return {**data, "id": str(len(created))}

        repo = _make_repo(create=AsyncMock(side_effect=_create))
        ds = RepositoryDataSource(repository=repo)
        results = await ds.bulk_create([{"name": "A"}, {"name": "B"}])
        assert len(results) == 2
        assert results[0]["name"] == "A"
        assert results[1]["name"] == "B"

    async def test_bulk_update_counts_successes(self) -> None:
        repo = _make_repo()
        ds = RepositoryDataSource(repository=repo)
        count = await ds.bulk_update(["1", "2", "3"], {"status": "reviewed"})
        assert count == 3
        assert repo.update.await_count == 3

    async def test_bulk_delete_counts_deleted(self) -> None:
        calls = {"n": 0}
        async def _delete(item_id: Any) -> bool:
            calls["n"] += 1
            return calls["n"] % 2 == 1  # odd ids succeed

        repo = _make_repo(delete=AsyncMock(side_effect=_delete))
        ds = RepositoryDataSource(repository=repo)
        count = await ds.bulk_delete(["a", "b", "c"])
        assert count == 2  # ids 1 and 3 succeed
