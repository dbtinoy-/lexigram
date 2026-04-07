"""Tests for InMemoryDataSource with QuerySpec."""
from __future__ import annotations

from lexigram.admin.data.adapters.memory_adapter import InMemoryDataSource
from lexigram.admin.data.query import FilterCondition, FilterOperator, QuerySpec


class TestInMemoryDataSourceQuerySpec:
    def setup_method(self) -> None:
        self.data = [
            {"id": 1, "name": "Alice", "status": "active"},
            {"id": 2, "name": "Bob", "status": "inactive"},
            {"id": 3, "name": "Charlie", "status": "active"},
        ]
        self.ds = InMemoryDataSource(self.data)

    async def test_find_many_basic(self) -> None:
        qs = QuerySpec()
        result = await self.ds.find_many(qs)
        assert result.total == 3
        assert len(result.items) == 3

    async def test_find_many_with_filter_eq(self) -> None:
        qs = QuerySpec(
            where=(FilterCondition(field="status", operator=FilterOperator.EQ, value="active"),),
        )
        result = await self.ds.find_many(qs)
        assert result.total == 2
        assert result.items[0]["name"] == "Alice"

    async def test_find_many_with_search(self) -> None:
        qs = QuerySpec(search="alice", search_fields=["name"])
        result = await self.ds.find_many(qs)
        assert result.total == 1
        assert result.items[0]["name"] == "Alice"

    async def test_find_many_with_pagination(self) -> None:
        qs = QuerySpec(page=1, per_page=2)
        result = await self.ds.find_many(qs)
        assert len(result.items) == 2
        assert result.total == 3
        assert result.has_next

    async def test_find_many_with_sort(self) -> None:
        qs = QuerySpec(sort_by="name", sort_order="desc")
        result = await self.ds.find_many(qs)
        assert result.items[0]["name"] == "Charlie"
        assert result.items[-1]["name"] == "Alice"

    async def test_count_with_query(self) -> None:
        qs = QuerySpec(where=(FilterCondition(field="status", operator=FilterOperator.EQ, value="active"),))
        count = await self.ds.count(qs)
        assert count == 2
