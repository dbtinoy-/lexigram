"""Tests for search models."""

import pytest

from lexigram.search.config import IndexConfig
from lexigram.search.types import (
    SearchQuery,
    SearchResponse,
    SearchResult,
    SearchStrategy,
)


class TestSearchResult:
    """Tests for SearchResult."""

    def test_search_result_creation(self) -> None:
        """Test creating a search result."""
        result = SearchResult(
            id="doc-1",
            score=0.95,
            data={"title": "Test"},
        )
        assert result.id == "doc-1"
        assert result.score == 0.95
        assert result.data == {"title": "Test"}
        assert result.highlights is None

    def test_search_result_with_highlights(self) -> None:
        """Test search result with highlights."""
        result = SearchResult(
            id="doc-1",
            score=0.95,
            data={"title": "Test"},
            highlights={"title": "<em>Test</em>"},
        )
        assert result.highlights == {"title": "<em>Test</em>"}


class TestSearchResponse:
    """Tests for SearchResponse."""

    def test_search_response_creation(self) -> None:
        """Test creating a search response."""
        results = [
            SearchResult(id="doc-1", score=0.9, data={}),
            SearchResult(id="doc-2", score=0.8, data={}),
        ]
        response = SearchResponse(results=results, total=100)
        assert len(response.results) == 2
        assert response.total == 100
        assert response.page == 1
        assert response.per_page == 20

    def test_search_response_with_pagination(self) -> None:
        """Test search response with pagination."""
        response = SearchResponse(
            results=[],
            total=100,
            page=3,
            per_page=10,
        )
        assert response.page == 3
        assert response.per_page == 10

    def test_search_response_with_facets(self) -> None:
        """Test search response with facets."""
        response = SearchResponse(
            results=[],
            total=0,
            facets={"category": {"books": 10, "electronics": 5}},
        )
        assert response.facets == {"category": {"books": 10, "electronics": 5}}


class TestIndexConfig:
    """Tests for IndexConfig."""

    def test_index_config_creation(self) -> None:
        """Test creating an index config."""
        config = IndexConfig(
            name="products",
            searchable_fields=["title", "description"],
        )
        assert config.name == "products"
        assert config.searchable_fields == ["title", "description"]
        assert config.primary_key == "id"

    def test_index_config_with_all_fields(self) -> None:
        """Test index config with all fields."""
        config = IndexConfig(
            name="products",
            searchable_fields=["title"],
            filterable_fields=["category"],
            sortable_fields=["price", "created_at"],
            primary_key="product_id",
        )
        assert config.filterable_fields == ["category"]
        assert config.sortable_fields == ["price", "created_at"]
        assert config.primary_key == "product_id"


class TestSearchQuery:
    """Tests for SearchQuery."""

    def test_search_query_creation(self) -> None:
        """Test creating a search query."""
        query = SearchQuery(query="test")
        assert query.query == "test"
        assert query.page == 1
        assert query.per_page == 20

    def test_search_query_with_filters(self) -> None:
        """Test search query with filters."""
        query = SearchQuery(
            query="test",
            filters={"category": "books"},
        )
        assert query.filters == {"category": "books"}

    def test_search_query_with_sorting(self) -> None:
        """Test search query with sorting."""
        query = SearchQuery(
            query="test",
            sort_by="price",
            sort_order="desc",
        )
        assert query.sort_by == "price"
        assert query.sort_order == "desc"


class TestSearchStrategy:
    """Tests for SearchStrategy."""

    def test_exact_strategy(self) -> None:
        """Test exact search strategy."""
        assert SearchStrategy.EXACT.value == "exact"

    def test_fuzzy_strategy(self) -> None:
        """Test fuzzy search strategy."""
        assert SearchStrategy.FUZZY.value == "fuzzy"

    def test_phrase_strategy(self) -> None:
        """Test phrase search strategy."""
        assert SearchStrategy.PHRASE.value == "phrase"

    def test_all_strategies_defined(self) -> None:
        """Test all strategies are defined."""
        strategies = list(SearchStrategy)
        assert len(strategies) == 3
