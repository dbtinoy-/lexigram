"""Tests for NullBackend."""
from __future__ import annotations

import pytest

from lexigram.contracts.core import HealthStatus
from lexigram.search.backends.null import NullBackend


class TestNullBackend:
    """Tests for NullBackend."""

    @pytest.fixture
    def backend(self) -> NullBackend:
        """Create NullBackend instance."""
        return NullBackend()

    @pytest.mark.asyncio
    async def test_index_returns_ok(self, backend: NullBackend) -> None:
        """Verify index returns Ok(True)."""
        result = await backend.index("test_index", [{"id": "1"}])
        assert result.is_ok()
        assert result.unwrap() is True

    @pytest.mark.asyncio
    async def test_update_returns_ok(self, backend: NullBackend) -> None:
        """Verify update returns Ok(True)."""
        result = await backend.update("test_index", "doc1", {"name": "updated"})
        assert result.is_ok()
        assert result.unwrap() is True

    @pytest.mark.asyncio
    async def test_delete_returns_ok(self, backend: NullBackend) -> None:
        """Verify delete returns Ok(True)."""
        result = await backend.delete("test_index", "doc1")
        assert result.is_ok()
        assert result.unwrap() is True

    @pytest.mark.asyncio
    async def test_search_returns_empty_response(self, backend: NullBackend) -> None:
        """Verify search returns empty SearchResponse."""
        result = await backend.search("test_index", "query")
        assert result.is_ok()
        response = result.unwrap()
        assert response.results == []
        assert response.total == 0
        assert response.query == "query"

    @pytest.mark.asyncio
    async def test_search_with_pagination(self, backend: NullBackend) -> None:
        """Verify search pagination is calculated correctly."""
        result = await backend.search("test_index", "query", limit=10, offset=20)
        assert result.is_ok()
        response = result.unwrap()
        assert response.per_page == 10
        assert response.page == 3  # 20/10 + 1

    @pytest.mark.asyncio
    async def test_search_with_zero_limit(self, backend: NullBackend) -> None:
        """Verify search handles zero limit without division error."""
        result = await backend.search("test_index", "query", limit=0, offset=0)
        assert result.is_ok()
        response = result.unwrap()
        assert response.per_page == 0

    @pytest.mark.asyncio
    async def test_search_with_filters(self, backend: NullBackend) -> None:
        """Verify search accepts filters."""
        result = await backend.search("test_index", "query", filters={"field": "value"})
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_search_with_sort(self, backend: NullBackend) -> None:
        """Verify search accepts sort."""
        result = await backend.search("test_index", "query", sort=["-field"])
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_create_index_returns_ok(self, backend: NullBackend) -> None:
        """Verify create_index returns Ok(True)."""
        result = await backend.create_index("test_index")
        assert result.is_ok()
        assert result.unwrap() is True

    @pytest.mark.asyncio
    async def test_create_index_with_settings(self, backend: NullBackend) -> None:
        """Verify create_index accepts settings."""
        result = await backend.create_index("test_index", {"analyzers": {}})
        assert result.is_ok()
        assert result.unwrap() is True

    @pytest.mark.asyncio
    async def test_delete_index_returns_ok(self, backend: NullBackend) -> None:
        """Verify delete_index returns Ok(True)."""
        result = await backend.delete_index("test_index")
        assert result.is_ok()
        assert result.unwrap() is True

    @pytest.mark.asyncio
    async def test_index_exists_returns_ok(self, backend: NullBackend) -> None:
        """Verify index_exists returns Ok(True)."""
        result = await backend.index_exists("test_index")
        assert result.is_ok()
        assert result.unwrap() is True

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy(self, backend: NullBackend) -> None:
        """Verify health_check returns healthy status."""
        result = await backend.health_check()
        assert result.status == HealthStatus.HEALTHY
        assert result.component == "search"
        assert result.details == {"backend": "NullBackend"}
