"""Unit tests for Typesense search backend."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

# Skip if typesense not available
try:
    import typesense
except ImportError:
    typesense = None

pytest.importorskip("typesense")

from lexigram.search.backends.typesense import TypesenseBackend
from lexigram.search.config import TypesenseConfig
from lexigram.search.types import SearchResponse, SearchResult


class TestTypesenseBackend:
    """Test TypesenseBackend functionality."""

    @pytest.fixture
    def mock_client(self):
        """Mock Typesense client."""
        client = MagicMock()

        # Mock collection
        collection = MagicMock()
        client.collections.__getitem__ = lambda self, key: collection

        # Mock documents.search as an async method
        collection.documents.search = AsyncMock(return_value={
            "hits": [
                {
                    "document": {"id": "1", "title": "Test 1"},
                    "score": 0.9
                },
                {
                    "document": {"id": "2", "title": "Test 2"},
                    "score": 0.8
                },
            ],
            "found": 2
        })

        # Mock document upsert/delete operations
        collection.documents.upsert = AsyncMock(return_value={})
        collection.documents.delete = AsyncMock()

        # Mock collection-level operations
        collection.retrieve = AsyncMock()
        client.collections.create = AsyncMock()

        return client

    @pytest.fixture
    def backend(self, mock_client):
        """Create backend instance with mocked client."""
        with patch("typesense.Client", return_value=mock_client):
            config = TypesenseConfig(
                api_url="http://localhost:8108",
                api_key="test_key",
            )
            backend = TypesenseBackend(config)
            backend._client = mock_client
            return backend

    @pytest.mark.asyncio
    async def test_index_document(self, backend, mock_client):
        """Test indexing documents."""
        result = await backend.index_document(
            "test_index",
            {"id": "1", "title": "Test Document", "content": "test content"}
        )

        assert result["id"] == "1"
        assert result["status"] == "indexed"

    @pytest.mark.asyncio
    async def test_search(self, backend, mock_client):
        """Test search operation returns Ok(SearchResponse)."""
        result = await backend.search("test_index", "test query", limit=10)

        assert result.is_ok()
        response = result.unwrap()
        assert isinstance(response, SearchResponse)
        assert len(response.results) == 2
        assert response.results[0].id == "1"
        assert response.results[0].score == 0.9
        assert response.total == 2

    @pytest.mark.asyncio
    async def test_search_with_filters(self, backend, mock_client):
        """Test search with filters returns Ok(SearchResponse)."""
        result = await backend.search(
            "test_index",
            "test query",
            filters={"category": "tech"},
            limit=10
        )

        assert result.is_ok()
        response = result.unwrap()
        assert len(response.results) == 2

    @pytest.mark.asyncio
    async def test_search_returns_err_on_backend_failure(self, backend, mock_client):
        """Test search returns Err(SearchError) when the backend raises."""
        from lexigram.search.exceptions import SearchError

        mock_client.collections.__getitem__ = MagicMock(
            side_effect=RuntimeError("connection refused")
        )

        result = await backend.search("test_index", "test query")

        assert result.is_err()
        assert isinstance(result.unwrap_err(), SearchError)

    @pytest.mark.asyncio
    async def test_delete_document(self, backend, mock_client):
        """Test deleting document."""
        result = await backend.delete_document("test_index", "1")

        assert result is True

    @pytest.mark.asyncio
    async def test_bulk_index(self, backend, mock_client):
        """Test bulk indexing."""
        mock_collection = MagicMock()
        mock_collection.documents.import_ = AsyncMock(return_value=[
            {"success": True},
            {"success": True},
        ])

        mock_client.collections.__getitem__ = lambda self, key: mock_collection

        result = await backend.bulk_index(
            "test_index",
            [
                {"id": "1", "title": "Test 1"},
                {"id": "2", "title": "Test 2"},
            ]
        )

        assert result["indexed"] == 2
