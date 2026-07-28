"""Unit tests for MeiliSearch backend."""

import pytest

pytest.importorskip("meilisearch")

from unittest.mock import MagicMock, AsyncMock, patch

from lexigram.search.backends.meilisearch import MeiliSearchBackend
from lexigram.search.types import SearchResponse

class TestMeiliSearchBackend:
    """Test MeiliSearchBackend functionality."""

    @pytest.fixture
    def mock_client(self):
        """Mock MeiliSearch client."""
        client = MagicMock()
        index = MagicMock()
        client.index.return_value = index
        return client

    @pytest.fixture
    def backend(self, mock_client):
        """Create backend instance with mocked client."""
        with patch("meilisearch.Client", return_value=mock_client):
            backend = MeiliSearchBackend(url="http://test:7700", api_key="key")
            # Force client init
            backend._client = mock_client
            return backend

    @pytest.mark.asyncio
    async def test_search(self, backend, mock_client):
        """Test search operation."""
        index_mock = mock_client.index.return_value
        index_mock.search.return_value = {
            "hits": [
                {"id": "1", "title": "Test 1", "_rankingScore": 0.9},
                {"id": "2", "title": "Test 2", "_rankingScore": 0.8}
            ],
            "estimatedTotalHits": 2,
            "processingTimeMs": 10
        }

        result = await backend.search("test_index", "query")

        assert result.is_ok()
        response = result.unwrap()
        assert isinstance(response, SearchResponse)
        assert len(response.results) == 2
        assert response.total == 2
        assert response.results[0].id == "1"
        assert response.results[0].score == 0.9

    @pytest.mark.asyncio
    async def test_index_document(self, backend, mock_client):
        """Test indexing documents."""
        index_mock = mock_client.index.return_value
        index_mock.add_documents.return_value = {"taskUid": 1}

        result = await backend.index("test_index", [{"id": "1", "data": "test"}])

        assert result.is_ok()
        assert result.unwrap() is True
        index_mock.add_documents.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete(self, backend, mock_client):
        """Test deleting document."""
        index_mock = mock_client.index.return_value
        index_mock.delete_document.return_value = {"taskUid": 2}

        result = await backend.delete("test_index", "1")

        assert result.is_ok()
        assert result.unwrap() is True
        index_mock.delete_document.assert_called_with("1")

    @pytest.mark.asyncio
    async def test_create_index(self, backend, mock_client):
        """Test creating index."""
        mock_client.create_index.return_value = {"taskUid": 3}

        result = await backend.create_index("new_index", {"primaryKey": "id"})

        assert result.is_ok()
        assert result.unwrap() is True
        mock_client.create_index.assert_called_with("new_index", {"primaryKey": "id"})

    @pytest.mark.asyncio
    async def test_delete_index(self, backend, mock_client):
        """Test deleting index."""
        mock_client.delete_index.return_value = {"taskUid": 4}

        result = await backend.delete_index("old_index")

        assert result.is_ok()
        assert result.unwrap() is True
        mock_client.delete_index.assert_called_with("old_index")
