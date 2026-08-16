"""Tests for search types."""

import pytest

from lexigram.search.types import (
    RAGSearchResult,
    SearchQuery,
    SearchResponse,
    SearchResult,
    SearchStrategy,
)


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_creation(self) -> None:
        """Test creating a SearchResult."""
        result = SearchResult(
            id="doc-1",
            score=0.95,
            data={"title": "Test Document"},
        )
        assert result.id == "doc-1"
        assert result.score == 0.95
        assert result.data == {"title": "Test Document"}
        assert result.highlights is None

    def test_creation_with_highlights(self) -> None:
        """Test creating a SearchResult with highlights."""
        result = SearchResult(
            id="doc-1",
            score=0.95,
            data={"title": "Test"},
            highlights={"title": "<em>Test</em>"},
        )
        assert result.highlights == {"title": "<em>Test</em>"}

    def test_is_frozen(self) -> None:
        """Test that SearchResult is immutable."""
        result = SearchResult(id="doc-1", score=0.5, data={})
        with pytest.raises(Exception):
            result.id = "new-id"

    def test_equality(self) -> None:
        """Test SearchResult equality."""
        r1 = SearchResult(id="doc-1", score=0.5, data={"x": 1})
        r2 = SearchResult(id="doc-1", score=0.5, data={"x": 1})
        assert r1 == r2


class TestSearchResponse:
    """Tests for SearchResponse dataclass."""

    def test_creation(self) -> None:
        """Test creating a SearchResponse."""
        results = [
            SearchResult(id="doc-1", score=0.9, data={}),
            SearchResult(id="doc-2", score=0.8, data={}),
        ]
        response = SearchResponse(
            results=results,
            total=100,
            query="test query",
        )
        assert len(response.results) == 2
        assert response.total == 100
        assert response.query == "test query"
        assert response.page == 1
        assert response.per_page == 20
        assert response.took_ms is None
        assert response.facets is None

    def test_creation_with_pagination(self) -> None:
        """Test creating a SearchResponse with pagination."""
        response = SearchResponse(
            results=[],
            total=50,
            page=3,
            per_page=10,
            query="test",
            took_ms=15.5,
        )
        assert response.page == 3
        assert response.per_page == 10
        assert response.took_ms == 15.5


class TestSearchQuery:
    """Tests for SearchQuery dataclass."""

    def test_creation(self) -> None:
        """Test creating a SearchQuery."""
        query = SearchQuery(query="test search")
        assert query.query == "test search"
        assert query.filters is None
        assert query.page == 1
        assert query.per_page == 20
        assert query.sort_by is None
        assert query.sort_order == "asc"

    def test_creation_with_filters(self) -> None:
        """Test creating a SearchQuery with filters."""
        query = SearchQuery(
            query="test",
            filters={"category": "books", "year": 2024},
        )
        assert query.filters == {"category": "books", "year": 2024}

    def test_creation_with_sorting(self) -> None:
        """Test creating a SearchQuery with sorting."""
        query = SearchQuery(
            query="test",
            sort_by="relevance",
            sort_order="desc",
        )
        assert query.sort_by == "relevance"
        assert query.sort_order == "desc"


class TestSearchStrategy:
    """Tests for SearchStrategy enum."""

    def test_exact_strategy(self) -> None:
        """Test EXACT strategy value."""
        assert SearchStrategy.EXACT == "exact"

    def test_fuzzy_strategy(self) -> None:
        """Test FUZZY strategy value."""
        assert SearchStrategy.FUZZY == "fuzzy"

    def test_phrase_strategy(self) -> None:
        """Test PHRASE strategy value."""
        assert SearchStrategy.PHRASE == "phrase"

    def test_is_str_enum(self) -> None:
        """Test that SearchStrategy is a string enum."""
        assert isinstance(SearchStrategy.EXACT, str)
        assert isinstance(SearchStrategy.FUZZY, str)
        assert isinstance(SearchStrategy.PHRASE, str)

    def test_all_strategies_defined(self) -> None:
        """Test all strategy values are defined."""
        strategies = list(SearchStrategy)
        assert len(strategies) == 3


class TestRAGSearchResultAlias:
    """Tests for RAGSearchResult alias."""

    def test_alias_points_to_search_result(self) -> None:
        """Test that RAGSearchResult is an alias for SearchResult."""
        assert RAGSearchResult is SearchResult