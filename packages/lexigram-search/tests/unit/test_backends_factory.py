"""Tests for search backend factory."""

import pytest
from unittest.mock import MagicMock, patch

from lexigram.search.backends.factory import get_backend
from lexigram.search import constants as search_const


class TestGetBackend:
    """Tests for get_backend factory function."""

    def test_get_meilisearch_backend(self) -> None:
        """Test getting MeiliSearch backend."""
        backend = get_backend(
            search_const.BACKEND_MEILISEARCH,
            api_key="test",
            host="http://localhost",
        )
        
        assert backend is not None

    def test_get_memory_backend(self) -> None:
        """Test getting memory (null) backend."""
        backend = get_backend(search_const.BACKEND_MEMORY)
        
        assert backend is not None

    def test_unknown_backend_raises(self) -> None:
        """Test unknown backend raises ValueError."""
        with pytest.raises(ValueError, match="Unknown backend"):
            get_backend("unknown_backend")

    @patch("lexigram.search.backends.factory._sqlite_available", True)
    @patch("lexigram.search.backends.factory.SQLiteSearchBackend")
    def test_get_sqlite_backend(self, mock_sqlite: MagicMock) -> None:
        """Test getting SQLite backend when available."""
        mock_instance = MagicMock()
        mock_sqlite.return_value = mock_instance
        
        backend = get_backend(search_const.BACKEND_SQLITE, db_path=":memory:")
        
        mock_sqlite.assert_called_once_with(db_path=":memory:")

    @patch("lexigram.search.backends.factory._mongodb_available", True)
    @patch("lexigram.search.backends.factory.MongoSearchBackend")
    def test_get_mongodb_backend(self, mock_mongo: MagicMock) -> None:
        """Test getting MongoDB backend when available."""
        mock_instance = MagicMock()
        mock_mongo.return_value = mock_instance
        
        backend = get_backend(
            search_const.BACKEND_MONGODB,
            connection_string="mongodb://localhost",
        )
        
        mock_mongo.assert_called_once_with(connection_string="mongodb://localhost")

    @patch("lexigram.search.backends.factory._elasticsearch_available", True)
    @patch("lexigram.search.backends.factory.ElasticsearchBackend")
    def test_get_elasticsearch_backend(self, mock_es: MagicMock) -> None:
        """Test getting Elasticsearch backend when available."""
        mock_instance = MagicMock()
        mock_es.return_value = mock_instance
        
        backend = get_backend(
            search_const.BACKEND_ELASTICSEARCH,
            hosts=["http://localhost:9200"],
        )
        
        mock_es.assert_called_once_with(hosts=["http://localhost:9200"])

    @patch("lexigram.search.backends.factory._typesense_available", True)
    @patch("lexigram.search.backends.factory.TypesenseBackend")
    def test_get_typesense_backend(self, mock_typesense: MagicMock) -> None:
        """Test getting Typesense backend when available."""
        mock_instance = MagicMock()
        mock_typesense.return_value = mock_instance
        
        backend = get_backend(
            search_const.BACKEND_TYPESENSE,
            api_key="test",
            host="http://localhost",
        )
        
        mock_typesense.assert_called_once()