"""Unit tests for search engine core."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.search.engine import DefaultSearchEngine, SearchConfig, SearchQuery
from lexigram.search.exceptions import SearchError
from lexigram.search.types import SearchResponse


class TestDefaultSearchEngine:
    """Test DefaultSearchEngine functionality."""

    @pytest.fixture
    def mock_backend(self):
        """Mock search backend."""
        backend = MagicMock()
        backend.search = AsyncMock()
        backend.index_document = AsyncMock()
        backend.get_document = AsyncMock()
        backend.delete_document = AsyncMock()
        backend.bulk_operation = AsyncMock()
        return backend

    @pytest.fixture
    def config(self):
        """Create search config."""
        config = MagicMock(spec=SearchConfig)
        config.max_limit = 100
        return config

    @pytest.fixture
    def engine(self, mock_backend, config):
        """Create engine instance."""
        return DefaultSearchEngine(backend=mock_backend, config=config)

    @pytest.mark.asyncio
    async def test_search(self, engine, mock_backend):
        """Test search returns Ok(response) on success."""
        mock_response = SearchResponse(
            results=[], total=0, page=1, per_page=20, query="test", took_ms=1
        )
        mock_backend.search.return_value = mock_response

        query = SearchQuery(q="test")
        result = await engine.search("index", query)

        assert result.is_ok()
        assert result.unwrap() == mock_response
        mock_backend.search.assert_called_with("index", query)

    @pytest.mark.asyncio
    async def test_search_error(self, engine, mock_backend):
        """Test search returns Err(SearchError) on backend failure."""
        mock_backend.search.side_effect = Exception("Backend fail")

        result = await engine.search("index", SearchQuery(q="test"))

        assert result.is_err()
        assert isinstance(result.unwrap_err(), SearchError)

    @pytest.mark.asyncio
    async def test_search_propagates_search_error(self, engine, mock_backend):
        """SearchError raised by the backend is returned as-is in Err()."""
        original = SearchError("already a search error")
        mock_backend.search.side_effect = original

        result = await engine.search("index", SearchQuery(q="test"))

        assert result.is_err()
        assert result.unwrap_err() is original

    @pytest.mark.asyncio
    async def test_index_document(self, engine, mock_backend):
        """Test indexing document."""
        mock_backend.index_document.return_value = True

        success = await engine.index_document("index", "1", {"data": "test"})

        assert success
        mock_backend.index_document.assert_called_with("1", {"data": "test"}, index_name="index")

    @pytest.mark.asyncio
    async def test_get_document(self, engine, mock_backend):
        """Test retrieving document."""
        mock_backend.get_document.return_value = {"id": "1"}

        doc = await engine.get_document("index", "1")

        assert doc == {"id": "1"}
        mock_backend.get_document.assert_called_with("index", "1")

    @pytest.mark.asyncio
    async def test_delete_document(self, engine, mock_backend):
        """Test deleting document."""
        mock_backend.delete_document.return_value = True

        success = await engine.delete_document("index", "1")

        assert success
        mock_backend.delete_document.assert_called_with("index", "1")

    @pytest.mark.asyncio
    async def test_index_many_delegates_to_bulk_operation(self, engine, mock_backend):
        """Test that index_many converts pairs to bulk operations and returns success count."""
        bulk_result = MagicMock()
        bulk_result.successful = 2
        bulk_result.failed = 0
        mock_backend.bulk_operation = AsyncMock(return_value=bulk_result)

        documents = [
            ("doc-1", {"title": "First"}),
            ("doc-2", {"title": "Second"}),
        ]
        count = await engine.index_many("my-index", documents)

        assert count == 2
        mock_backend.bulk_operation.assert_called_once()
        call_args = mock_backend.bulk_operation.call_args
        ops = call_args[0][1]  # positional arg: operations list
        assert len(ops) == 2
        assert ops[0] == {
            "operation": "index",
            "id": "doc-1",
            "document": {"title": "First"},
        }
        assert ops[1] == {
            "operation": "index",
            "id": "doc-2",
            "document": {"title": "Second"},
        }

    @pytest.mark.asyncio
    async def test_index_many_empty_list_returns_zero(self, engine, mock_backend):
        """Test that index_many with an empty list returns 0 without calling bulk_operation."""
        mock_backend.bulk_operation = AsyncMock()

        count = await engine.index_many("my-index", [])

        assert count == 0
        mock_backend.bulk_operation.assert_not_called()
