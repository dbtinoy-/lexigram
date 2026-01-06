"""Unit tests for the new Data Handling System."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.data.adapters.memory_adapter import InMemoryDataSource
from lexigram.admin.data.adapters.repository import RepositoryDataSource
from lexigram.admin.data.query import FilterCondition, FilterOperator, QuerySpec


class TestInMemoryDataSource:
    @pytest.mark.asyncio
    async def test_find_many(self):
        data = [
            {"id": 1, "name": "Alice", "role": "admin"},
            {"id": 2, "name": "Bob", "role": "user"},
            {"id": 3, "name": "Charlie", "role": "user"},
        ]
        ds = InMemoryDataSource(data)

        query = QuerySpec(where=(FilterCondition(field="role", operator=FilterOperator.EQ, value="user"),))
        result = await ds.find_many(query)

        assert result.total == 2
        assert len(result.items) == 2
        assert result.items[0]["name"] == "Bob"

    @pytest.mark.asyncio
    async def test_pagination(self):
        data = list(map(lambda i: {"id": i, "name": f"User {i}"}, range(1, 11)))
        ds = InMemoryDataSource(data)

        query = QuerySpec(page=2, per_page=3)
        result = await ds.find_many(query)

        assert result.total == 10
        assert len(result.items) == 3
        assert result.items[0]["id"] == 4
        assert result.has_next is True
        assert result.has_prev is True


class TestRepositoryDataSource:
    @pytest.mark.asyncio
    async def test_repository_adapter(self):
        # Arrange
        mock_repo = MagicMock()
        mock_repo.find_many = AsyncMock(return_value=[{"id": 1, "name": "Alice"}])
        mock_repo.count = AsyncMock(return_value=1)

        ds = RepositoryDataSource(mock_repo)
        query = QuerySpec(where=(FilterCondition(field="status", operator=FilterOperator.EQ, value="active"),))

        # Act
        result = await ds.find_many(query)

        # Assert
        assert result.total == 1
        assert result.items[0]["name"] == "Alice"
        mock_repo.find_many.assert_called_once()
        # Verify filters were passed through
        args, kwargs = mock_repo.find_many.call_args
        assert kwargs["filters"] is not None
