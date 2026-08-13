"""Unit tests for batch indexing."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.search.engine import SearchEngine
from lexigram.search.indexing.batch import BatchConfig, BatchIndexer


class TestBatchIndexer:
    """Test BatchIndexer functionality."""

    @pytest.fixture
    def mock_engine(self):
        """Mock search engine."""
        engine = MagicMock(spec=SearchEngine)
        engine.bulk_operation = AsyncMock()
        return engine

    @pytest.fixture
    def indexer(self, mock_engine):
        """Create batch indexer."""
        config = BatchConfig(batch_size=2, retry_attempts=1)
        return BatchIndexer(engine=mock_engine, config=config)

    @pytest.mark.asyncio
    async def test_index_documents(self, indexer, mock_engine):
        """Test batch indexing documents."""
        # Setup mock return for bulk operation
        mock_result = MagicMock()
        mock_result.successful = 2
        mock_result.failed = 0
        mock_engine.bulk_operation.return_value = mock_result

        documents = [{"id": "1", "val": "a"}, {"id": "2", "val": "b"}]
        stats = await indexer.index_documents("index", documents)

        assert stats.total_documents == 2
        assert stats.processed_documents == 2
        assert stats.successful_operations == 2
        # Should be called once as batch size is 2 and we have 2 docs
        mock_engine.bulk_operation.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_documents_chunking(self, indexer, mock_engine):
        """Test batch chunking."""
        mock_result = MagicMock()
        mock_result.successful = 2
        mock_result.failed = 0
        mock_engine.bulk_operation.return_value = mock_result

        # 3 documents, batch size 2 -> 2 calls
        documents = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        stats = await indexer.index_documents("index", documents)

        assert stats.total_documents == 3
        assert mock_engine.bulk_operation.call_count == 2  # 1 batch of 2, 1 batch of 1

    @pytest.mark.asyncio
    async def test_retry_logic(self, indexer, mock_engine):
        """Test retry logic on failure."""
        # First call fails, second succeeds
        mock_engine.bulk_operation.side_effect = [
            ValueError("Transient error"),
            MagicMock(successful=2, failed=0),
        ]

        # Increase retries for this test
        indexer.config.retry_attempts = 2
        indexer.config.retry_delay = 0.01

        documents = [{"id": "1"}, {"id": "2"}]
        stats = await indexer.index_documents("index", documents)

        assert stats.successful_operations == 2
        assert mock_engine.bulk_operation.call_count == 2

    @pytest.mark.asyncio
    async def test_delete_documents(self, indexer, mock_engine):
        """Test batch deletion."""
        mock_result = MagicMock()
        mock_result.successful = 2
        mock_result.failed = 0
        mock_engine.bulk_operation.return_value = mock_result

        ids = ["1", "2"]
        stats = await indexer.delete_documents("index", ids)

        assert stats.total_documents == 2
        mock_engine.bulk_operation.assert_called_once()
        args = mock_engine.bulk_operation.call_args[0]
        ops = args[1]
        assert ops[0]["operation"] == "delete"
        assert ops[0]["id"] == "1"
