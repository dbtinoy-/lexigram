from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from lexigram.admin.data.data_source import QueryResult
from lexigram.admin.data.query import QuerySpec
from lexigram.admin.integrations.search_query import SearchQueryDataSourceWrapper

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


@dataclass
class _FakeSearchResult:
    """Matches shape of SearchResult (id + data)."""
    id: str
    data: dict | None = None


@dataclass
class _FakeSearchResponse:
    """Matches shape of SearchResponse (total + results)."""
    results: list[_FakeSearchResult]
    total: int = 0


class _FakeOk:
    """Minimal Result[SearchResponse] double — matches is_ok / unwrap."""
    def __init__(self, value: _FakeSearchResponse) -> None:
        self._value = value

    def is_ok(self) -> bool:
        return True

    def unwrap(self) -> _FakeSearchResponse:
        return self._value


class _FakeErr:
    """Minimal Err double — is_ok returns False."""
    def is_ok(self) -> bool:
        return False


class _FakeSearchEngine:
    """Minimal search engine double for testing."""

    def __init__(self) -> None:
        self.search = AsyncMock(return_value=_FakeOk(_FakeSearchResponse([], total=0)))


class _InnerDataSource:
    """Simple IDataSource double that records calls."""

    def __init__(self) -> None:
        self._items: list[dict] = []
        self._count: int = 0
        self.find_many = AsyncMock(return_value=QueryResult(items=[], total=0))
        self.count = AsyncMock(return_value=0)

    async def find_one(self, item_id: object) -> object | None:
        return None

    async def find_many(self, query: QuerySpec) -> QueryResult:
        return await self.find_many(query)

    async def count(self, query: QuerySpec) -> int:
        return await self.count(query)

    async def create(self, data: dict) -> dict:
        return {**data, "id": 999}

    async def update(self, item_id: object, data: dict) -> dict:
        return {**data, "id": item_id}

    async def delete(self, item_id: object) -> bool:
        return True

    async def bulk_create(self, items: list[dict]) -> list[dict]:
        return items

    async def bulk_update(self, ids: list, data: dict) -> int:
        return len(ids)

    async def bulk_delete(self, ids: list) -> int:
        return len(ids)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def search_engine() -> _FakeSearchEngine:
    return _FakeSearchEngine()


@pytest.fixture
def inner() -> _InnerDataSource:
    return _InnerDataSource()


@pytest.fixture
def wrapper(inner: _InnerDataSource, search_engine: _FakeSearchEngine) -> SearchQueryDataSourceWrapper:
    return SearchQueryDataSourceWrapper(inner, search_engine, "test_idx")


# ---------------------------------------------------------------------------
# find_many — no search (passthrough)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_many_without_search_delegates_to_inner(
    wrapper: SearchQueryDataSourceWrapper,
    inner: _InnerDataSource,
) -> None:
    query = QuerySpec(page=1, per_page=20)
    inner.find_many.return_value = QueryResult(items=[{"id": 1}], total=1)

    result = await wrapper.find_many(query)

    inner.find_many.assert_awaited_once_with(query)
    assert result.total == 1
    assert len(result.items) == 1
    assert result.items[0]["id"] == 1


# ---------------------------------------------------------------------------
# find_many — with search (FTS routing)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_many_with_search_queries_fts_and_filters_by_ids(
    wrapper: SearchQueryDataSourceWrapper,
    inner: _InnerDataSource,
    search_engine: _FakeSearchEngine,
) -> None:
    total_count = 30
    all_ids = [str(i) for i in range(1, total_count + 1)]
    search_engine.search.return_value = _FakeOk(
        _FakeSearchResponse(
            results=[_FakeSearchResult(id=i) for i in all_ids],
            total=total_count,
        )
    )
    inner.find_many.return_value = QueryResult(
        items=[{"id": 1}], total=total_count, page=1, per_page=20
    )
    query = QuerySpec(search="test", search_fields=["name"], page=1, per_page=20)

    result = await wrapper.find_many(query)

    search_engine.search.assert_awaited_once_with(
        index_name="test_idx", query="test", limit=20, offset=0
    )
    call_args, _ = inner.find_many.await_args
    passed_query = call_args[0]
    assert passed_query.search is None
    assert passed_query.filters.get("id__in") == all_ids[:20]
    assert result.total == total_count


@pytest.mark.asyncio
async def test_find_many_with_search_no_matches_falls_back_to_like(
    wrapper: SearchQueryDataSourceWrapper,
    inner: _InnerDataSource,
    search_engine: _FakeSearchEngine,
) -> None:
    search_engine.search.return_value = _FakeOk(
        _FakeSearchResponse(results=[], total=0)
    )
    inner.find_many.return_value = QueryResult(
        items=[{"id": 1}], total=1, page=1, per_page=20
    )
    query = QuerySpec(search="xyz", search_fields=["name"], page=1, per_page=20)

    result = await wrapper.find_many(query)

    inner.find_many.assert_awaited_once_with(query)
    assert result.total == 1
    assert len(result.items) == 1


@pytest.mark.asyncio
async def test_find_many_with_search_no_matches_returns_empty_when_fallback_disabled(
    inner: _InnerDataSource,
    search_engine: _FakeSearchEngine,
) -> None:
    wrapper = SearchQueryDataSourceWrapper(
        inner, search_engine, "test_idx", fallback_to_like=False
    )
    search_engine.search.return_value = _FakeOk(
        _FakeSearchResponse(results=[], total=0)
    )
    query = QuerySpec(search="xyz", search_fields=["name"], page=1, per_page=20)

    result = await wrapper.find_many(query)

    inner.find_many.assert_not_awaited()
    assert result.total == 0
    assert len(result.items) == 0


@pytest.mark.asyncio
async def test_find_many_with_search_engine_error_falls_through(
    wrapper: SearchQueryDataSourceWrapper,
    inner: _InnerDataSource,
    search_engine: _FakeSearchEngine,
) -> None:
    search_engine.search.side_effect = RuntimeError("search down")
    inner.find_many.return_value = QueryResult(
        items=[{"id": 1}], total=1, page=1, per_page=20
    )
    query = QuerySpec(search="test", search_fields=["name"], page=1, per_page=20)

    result = await wrapper.find_many(query)

    inner.find_many.assert_awaited_once()
    call_args, _ = inner.find_many.await_args
    passed_query = call_args[0]
    assert passed_query.search is None
    assert result.total == 1


@pytest.mark.asyncio
async def test_find_many_with_search_err_result_falls_through(
    wrapper: SearchQueryDataSourceWrapper,
    inner: _InnerDataSource,
    search_engine: _FakeSearchEngine,
) -> None:
    search_engine.search.return_value = _FakeErr()
    inner.find_many.return_value = QueryResult(
        items=[{"id": 1}], total=1, page=1, per_page=20
    )
    query = QuerySpec(search="test", search_fields=["name"], page=1, per_page=20)

    result = await wrapper.find_many(query)

    inner.find_many.assert_awaited_once()
    call_args, _ = inner.find_many.await_args
    passed_query = call_args[0]
    assert passed_query.search is None
    assert result.total == 1


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_count_without_search_delegates_to_inner(
    wrapper: SearchQueryDataSourceWrapper,
    inner: _InnerDataSource,
) -> None:
    inner.count.return_value = 42
    query = QuerySpec(page=1, per_page=20)

    total = await wrapper.count(query)

    inner.count.assert_awaited_once_with(query)
    assert total == 42


@pytest.mark.asyncio
async def test_count_with_search_returns_fts_total(
    wrapper: SearchQueryDataSourceWrapper,
    inner: _InnerDataSource,
    search_engine: _FakeSearchEngine,
) -> None:
    search_engine.search.return_value = _FakeOk(
        _FakeSearchResponse(
            results=[_FakeSearchResult(id=str(i)) for i in range(1, 11)],
            total=10,
        )
    )
    query = QuerySpec(search="test", search_fields=["name"], page=1, per_page=20)

    total = await wrapper.count(query)

    search_engine.search.assert_awaited_once()
    inner.count.assert_not_awaited()
    assert total == 10


@pytest.mark.asyncio
async def test_count_with_search_engine_error_falls_through(
    wrapper: SearchQueryDataSourceWrapper,
    inner: _InnerDataSource,
    search_engine: _FakeSearchEngine,
) -> None:
    search_engine.search.side_effect = RuntimeError("search down")
    inner.count.return_value = 42
    query = QuerySpec(search="test", search_fields=["name"], page=1, per_page=20)

    total = await wrapper.count(query)

    inner.count.assert_awaited_once()
    assert total == 42


# ---------------------------------------------------------------------------
# Delegation: CRUD and other methods pass through
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_one_delegates(wrapper: SearchQueryDataSourceWrapper, inner: _InnerDataSource) -> None:
    result = await wrapper.find_one(1)
    assert result is None


@pytest.mark.asyncio
async def test_create_delegates(wrapper: SearchQueryDataSourceWrapper, inner: _InnerDataSource) -> None:
    result = await wrapper.create({"name": "test"})
    assert result["id"] == 999


@pytest.mark.asyncio
async def test_update_delegates(wrapper: SearchQueryDataSourceWrapper, inner: _InnerDataSource) -> None:
    result = await wrapper.update(1, {"name": "updated"})
    assert result["id"] == 1


@pytest.mark.asyncio
async def test_delete_delegates(wrapper: SearchQueryDataSourceWrapper, inner: _InnerDataSource) -> None:
    result = await wrapper.delete(1)
    assert result is True


@pytest.mark.asyncio
async def test_bulk_create_delegates(wrapper: SearchQueryDataSourceWrapper, inner: _InnerDataSource) -> None:
    result = await wrapper.bulk_create([{"name": "a"}])
    assert len(result) == 1


@pytest.mark.asyncio
async def test_bulk_update_delegates(wrapper: SearchQueryDataSourceWrapper, inner: _InnerDataSource) -> None:
    result = await wrapper.bulk_update([1, 2], {"name": "x"})
    assert result == 2


@pytest.mark.asyncio
async def test_bulk_delete_delegates(wrapper: SearchQueryDataSourceWrapper, inner: _InnerDataSource) -> None:
    result = await wrapper.bulk_delete([1, 2])
    assert result == 2
