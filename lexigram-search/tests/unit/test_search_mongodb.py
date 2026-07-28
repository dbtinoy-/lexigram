"""Unit tests for MongoDB search backend."""

import pytest

pytest.importorskip("motor")

from unittest.mock import MagicMock, AsyncMock, patch

from lexigram.search.backends.mongodb import MongoSearchBackend
from lexigram.search.config import MongoSearchConfig


class AsyncIteratorMock:
    """Mock for async iterators."""

    def __init__(self, items):
        self.items = list(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.items:
            return self.items.pop(0)
        raise StopAsyncIteration

    async def to_list(self, length=None):
        """Return all items as a list, compatible with Motor cursor API."""
        return list(self.items)


class TestMongoSearchBackend:
    """Test MongoSearchBackend functionality."""

    @pytest.fixture
    def mock_client(self):
        """Mock MongoDB client."""
        client = MagicMock()
        db = MagicMock()
        collection = MagicMock()
        
        client.__getitem__ = lambda self, key: db
        db.__getitem__ = lambda self, key: collection
        
        # Mock async methods
        collection.replace_one = AsyncMock(return_value=MagicMock(deleted_count=1))
        collection.aggregate = MagicMock(return_value=AsyncIteratorMock([
            {"_id": "1", "document": {"id": "1", "title": "Test 1"}, "score": 0.9},
            {"_id": "2", "document": {"id": "2", "title": "Test 2"}, "score": 0.8},
        ]))
        collection.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
        collection.list_indexes = MagicMock(return_value=AsyncIteratorMock([]))
        collection.create_index = AsyncMock()
        
        return client

    @pytest.fixture
    def backend(self, mock_client):
        """Create backend instance with mocked client."""
        with patch("motor.motor_asyncio.AsyncIOMotorClient", return_value=mock_client):
            config = MongoSearchConfig(
                connection_string="mongodb://localhost:27017",
                database_name="test",
            )
            backend = MongoSearchBackend(config)
            backend._client = mock_client
            backend._db = mock_client["test"]
            return backend

    @pytest.mark.asyncio
    async def test_index_document(self, backend, mock_client):
        """Test indexing documents."""
        db = mock_client["test"]
        collection = db["test_index"]
        
        result = await backend.index_document(
            "test_index",
            {"id": "1", "title": "Test Document", "content": "test content"}
        )
        
        assert result["id"] == "1"
        assert result["status"] == "indexed"

    @pytest.mark.asyncio
    async def test_search(self, backend, mock_client):
        """Test search operation."""
        # Create a mock cursor that returns results
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[
            {"_id": "1", "document": {"id": "1", "title": "Test 1"}, "score": 0.9},
            {"_id": "2", "document": {"id": "2", "title": "Test 2"}, "score": 0.8},
        ])
        
        db = mock_client["test"]
        collection = db["test_index"]
        collection.aggregate = MagicMock(return_value=mock_cursor)
        
        response = await backend.search("test_index", "test query", limit=10)
        
        assert response["hits"][0]["id"] == "1"
        assert response["hits"][0]["_score"] == 0.9

    @pytest.mark.asyncio
    async def test_delete_document(self, backend, mock_client):
        """Test deleting document."""
        db = mock_client["test"]
        collection = db["test_index"]
        
        result = await backend.delete_document("test_index", "1")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_extract_searchable_text(self, backend):
        """Test searchable text extraction."""
        doc = {
            "id": "1",
            "title": "Test Title",
            "description": "Test Description",
            "content": "Test Content",
        }
        
        text = backend._extract_searchable_text(doc)
        
        assert "Test Title" in text
        assert "Test Description" in text
        assert "Test Content" in text
