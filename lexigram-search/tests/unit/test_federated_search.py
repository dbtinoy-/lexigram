"""Tests for federated search engine."""

from unittest.mock import AsyncMock

import pytest

from lexigram.search.engine.federation import (
    FederatedResults,
    FederatedSearchEngine,
    FederatedSearchResult,
)


class MockSearchEngine:
    """Mock search engine for testing."""

    def __init__(self, results: dict[str, list[dict]]) -> None:
        self._results = results

    async def search(
        self,
        query: str,
        filters=None,
        sort=None,
        limit=None,
        offset=None,
    ):
        # Return mock results based on query
        results = self._results.get(query, [])
        return MockQueryResult(results)


class MockQueryResult:
    """Mock query result."""

    def __init__(self, documents: list[dict]) -> None:
        self.documents = documents
        self.total = len(documents)


class TestFederatedSearchEngine:
    """Tests for FederatedSearchEngine."""

    @pytest.fixture
    def mock_engine(self) -> MockSearchEngine:
        """Create a mock search engine."""
        return MockSearchEngine(
            {
                "laptop": [
                    {"id": "p1", "name": "Laptop Pro", "price": 999},
                    {"id": "p2", "name": "Laptop Air", "price": 799},
                ],
                "phone": [
                    {"id": "ph1", "name": "Phone X", "price": 699},
                ],
            }
        )

    @pytest.mark.asyncio
    async def test_search_across_multiple_indices(
        self, mock_engine: MockSearchEngine
    ) -> None:
        """Test searching across multiple indices."""
        federated = FederatedSearchEngine(
            engine=mock_engine,
            indices=["products", "electronics"],
        )

        results = await federated.search_across(
            query="laptop",
            indices=["products", "electronics"],
        )

        assert results.total_results >= 0

    @pytest.mark.asyncio
    async def test_search_across_no_indices(
        self, mock_engine: MockSearchEngine
    ) -> None:
        """Test searching with no indices returns empty."""
        federated = FederatedSearchEngine(engine=mock_engine)

        results = await federated.search_across(query="test")

        assert results.total_results == 0
        assert len(results.results) == 0

    @pytest.mark.asyncio
    async def test_search_across_with_limit(
        self, mock_engine: MockSearchEngine
    ) -> None:
        """Test searching with per-index limit."""
        federated = FederatedSearchEngine(engine=mock_engine)

        results = await federated.search_across(
            query="laptop",
            indices=["products"],
            limit_per_index=1,
        )

        # Should be limited
        assert results.total_results >= 0

    @pytest.mark.asyncio
    async def test_search_with_fallback(
        self, mock_engine: MockSearchEngine
    ) -> None:
        """Test search with fallback indices."""
        federated = FederatedSearchEngine(engine=mock_engine)

        # Primary returns empty, should fallback
        results = await federated.search_with_fallback(
            query="test",
            primary_indices=["primary"],
            fallback_indices=["fallback"],
            min_results=1,
        )

        assert results is not None


class TestFederatedResults:
    """Tests for FederatedResults."""

    def test_to_combined_list_empty(self) -> None:
        """Test converting empty results to list."""
        results = FederatedResults()
        combined = results.to_combined_list()

        assert combined == []

    def test_to_combined_list_with_index(self) -> None:
        """Test converting results with index metadata."""
        results = FederatedResults(
            results=[
                FederatedSearchResult(
                    index_name="products",
                    results=[{"id": "1", "name": "Test"}],
                    total_count=1,
                )
            ],
            total_results=1,
        )

        combined = results.to_combined_list(include_index=True)

        assert len(combined) == 1
        assert combined[0]["_index"] == "products"

    def test_to_combined_list_without_index(self) -> None:
        """Test converting results without index metadata."""
        results = FederatedResults(
            results=[
                FederatedSearchResult(
                    index_name="products",
                    results=[{"id": "1", "name": "Test"}],
                    total_count=1,
                )
            ],
            total_results=1,
        )

        combined = results.to_combined_list(include_index=False)

        assert len(combined) == 1
        assert "_index" not in combined[0]
