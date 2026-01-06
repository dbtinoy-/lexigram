"""Unit tests for Elasticsearch search backend."""

import pytest

pytest.importorskip("elasticsearch")

from unittest.mock import MagicMock, AsyncMock, patch

from lexigram.search.backends.elasticsearch import ElasticsearchBackend
from lexigram.search.config import ElasticsearchConfig
from lexigram.search.types import SearchResponse, SearchResult


class TestElasticsearchBackend:
    """Test ElasticsearchBackend functionality."""

    @pytest.fixture
    def mock_client(self):
        """Mock Elasticsearch client."""
        client = MagicMock()
        
        # Mock search response
        client.search = AsyncMock(return_value={
            "hits": {
                "hits": [
                    {
                        "_id": "1",
                        "_score": 0.9,
                        "_source": {"id": "1", "title": "Test 1"},
                        "highlight": {"title": ["<em>Test</em> 1"]}
                    },
                    {
                        "_id": "2", 
                        "_score": 0.8,
                        "_source": {"id": "2", "title": "Test 2"}
                    },
                ],
                "total": {"value": 2}
            }
        })
        
        client.index = AsyncMock()
        client.delete = AsyncMock()
        client.indices.exists = AsyncMock(return_value=True)
        client.indices.create = AsyncMock()
        
        return client

    @pytest.fixture
    def backend(self, mock_client):
        """Create backend instance with mocked client."""
        with patch("elasticsearch.AsyncElasticsearch", return_value=mock_client):
            config = ElasticsearchConfig(
                hosts=["http://localhost:9200"],
                index_prefix="test_",
            )
            backend = ElasticsearchBackend(config)
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

        mock_client.search.side_effect = RuntimeError("connection refused")

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
        mock_client.bulk = AsyncMock(return_value={
            "errors": False,
            "items": [{"index": {"status": 201}}]
        })
        
        result = await backend.bulk_index(
            "test_index",
            [
                {"id": "1", "title": "Test 1"},
                {"id": "2", "title": "Test 2"},
            ]
        )
        
        assert result["indexed"] == 2
