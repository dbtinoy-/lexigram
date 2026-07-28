"""Tests for ReindexManager."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.search.indexing.reindex import ReindexManager


class TestReindexManager:
    """Tests for ReindexManager."""

    @pytest.fixture
    def mock_engine(self) -> MagicMock:
        """Create a mock search engine."""
        engine = MagicMock()
        engine.create_index = AsyncMock()
        engine.delete_index = AsyncMock()
        engine.index_exists = AsyncMock(return_value=True)
        engine.rename_index = AsyncMock()
        engine.__class__.__name__ = "MockEngine"
        return engine

    @pytest.fixture
    def manager(self, mock_engine: MagicMock) -> ReindexManager:
        """Create ReindexManager with mock engine."""
        return ReindexManager(engine=mock_engine, batch_size=50)

    def test_detect_backend_type(self, mock_engine: MagicMock) -> None:
        """Verify backend type detection."""
        manager = ReindexManager(engine=mock_engine)
        assert manager._backend_type is None  # "mockengine" doesn't match

    def test_detect_elasticsearch_backend(self) -> None:
        """Verify elasticsearch backend detection."""
        es_engine = MagicMock()
        es_engine.__class__.__name__ = "ElasticsearchBackend"
        manager = ReindexManager(engine=es_engine)
        assert manager._backend_type == "elasticsearch"

    @pytest.mark.asyncio
    async def test_reindex_empty_source(self, manager: ReindexManager, mock_engine: MagicMock) -> None:
        """Verify reindex with empty source creates shadow index and swaps."""
        async def empty_gen():
            if False:
                yield

        result = await manager.reindex("users", source=empty_gen())

        assert result["indexed"] == 0
        assert result["failed"] == 0
        assert "shadow_index" in result
        mock_engine.create_index.assert_called_once()
        mock_engine.delete_index.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reindex_with_documents(self, manager: ReindexManager, mock_engine: MagicMock) -> None:
        """Verify reindex indexes documents and swaps."""
        mock_engine.index_many = AsyncMock(return_value={"indexed": 2, "failed": 0})

        async def doc_source():
            yield {"id": "1", "name": "Alice"}
            yield {"id": "2", "name": "Bob"}

        result = await manager.reindex("users", source=doc_source())

        assert result["indexed"] == 2
        assert result["failed"] == 0
        mock_engine.index_many.assert_called_once()

    @pytest.mark.asyncio
    async def test_reindex_multiple_batches(self, manager: ReindexManager, mock_engine: MagicMock) -> None:
        """Verify reindex handles multiple batches."""
        mock_engine.index_many = AsyncMock(side_effect=lambda _name, batch: {"indexed": len(batch), "failed": 0})

        async def doc_source():
            for i in range(120):
                yield {"id": str(i), "name": f"User {i}"}

        result = await manager.reindex("users", source=doc_source())

        assert result["indexed"] == 120
        assert result["failed"] == 0
        assert mock_engine.index_many.await_count == 3

    @pytest.mark.asyncio
    async def test_reindex_source_error_cleans_up(self, manager: ReindexManager, mock_engine: MagicMock) -> None:
        """Verify source error cleans up shadow index."""
        async def failing_source():
            yield {"id": "1"}
            raise RuntimeError("Source failure")

        with pytest.raises(RuntimeError, match="Source failure"):
            await manager.reindex("users", source=failing_source())

        mock_engine.delete_index.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_swap_deletes_old_index(self, manager: ReindexManager, mock_engine: MagicMock) -> None:
        """Verify fallback swap deletes old index."""
        mock_engine.index_exists = AsyncMock(return_value=True)
        mock_engine.rename_index = AsyncMock()

        await manager._fallback_swap("users", "users_reindex_123")

        mock_engine.delete_index.assert_awaited_once_with("users")
        mock_engine.rename_index.assert_awaited_once_with("users_reindex_123", "users")

    @pytest.mark.asyncio
    async def test_fallback_swap_no_old_index(self, manager: ReindexManager, mock_engine: MagicMock) -> None:
        """Verify fallback swap works when old index doesn't exist."""
        mock_engine.index_exists = AsyncMock(return_value=False)
        mock_engine.rename_index = AsyncMock()

        await manager._fallback_swap("users", "users_reindex_123")

        mock_engine.delete_index.assert_not_called()
        mock_engine.rename_index.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fallback_swap_rename_not_supported(self, manager: ReindexManager, mock_engine: MagicMock) -> None:
        """Verify fallback handles missing rename_index gracefully."""
        mock_engine.index_exists = AsyncMock(return_value=False)
        mock_engine.rename_index = AsyncMock(side_effect=NotImplementedError)

        await manager._fallback_swap("users", "users_reindex_123")

        mock_engine.rename_index.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_alias_swap_elasticsearch(self) -> None:
        """Verify alias swap for Elasticsearch backend."""
        es_engine = MagicMock()
        es_engine.__class__.__name__ = "ElasticsearchBackend"
        es_engine.create_index = AsyncMock()
        es_engine.delete_index = AsyncMock()
        es_engine.index_exists = AsyncMock(return_value=False)
        es_engine.index_many = AsyncMock(return_value={"indexed": 0, "failed": 0})

        manager = ReindexManager(engine=es_engine)
        assert manager._backend_type == "elasticsearch"

        mock_client = AsyncMock()
        mock_backend = MagicMock()
        mock_backend._get_client = AsyncMock(return_value=mock_client)
        es_engine._backend = mock_backend

        await manager._alias_swap("users", "users_reindex_123")

        mock_client.indices.put_alias.assert_awaited_once_with(
            index="users_reindex_123",
            name="users",
        )

    @pytest.mark.asyncio
    async def test_alias_swap_removes_old_alias(self) -> None:
        """Verify alias swap removes existing alias before adding new one."""
        es_engine = MagicMock()
        es_engine.__class__.__name__ = "ElasticsearchBackend"
        es_engine.create_index = AsyncMock()
        es_engine.delete_index = AsyncMock()
        es_engine.index_exists = AsyncMock(return_value=True)
        es_engine.index_many = AsyncMock(return_value={"indexed": 0, "failed": 0})

        manager = ReindexManager(engine=es_engine)

        mock_client = AsyncMock()
        mock_backend = MagicMock()
        mock_backend._get_client = AsyncMock(return_value=mock_client)
        es_engine._backend = mock_backend

        await manager._alias_swap("users", "users_reindex_123")

        mock_client.indices.delete_alias.assert_awaited_once_with(
            index="users",
            name="users",
        )
        mock_client.indices.put_alias.assert_awaited_once()
        es_engine.delete_index.assert_awaited_once_with("users")

    @pytest.mark.asyncio
    async def test_perform_swap_delegates_to_alias_for_es(self) -> None:
        """Verify _perform_swap delegates to _alias_swap for ES backend."""
        es_engine = MagicMock()
        es_engine.__class__.__name__ = "ElasticsearchBackend"
        manager = ReindexManager(engine=es_engine)
        manager._alias_swap = AsyncMock()
        manager._fallback_swap = AsyncMock()

        await manager._perform_swap("users", "shadow")

        manager._alias_swap.assert_awaited_once_with("users", "shadow")
        manager._fallback_swap.assert_not_called()

    @pytest.mark.asyncio
    async def test_perform_swap_delegates_to_fallback(self, manager: ReindexManager) -> None:
        """Verify _perform_swap delegates to _fallback_swap for non-ES."""
        manager._alias_swap = AsyncMock()
        manager._fallback_swap = AsyncMock()

        await manager._perform_swap("users", "shadow")

        manager._fallback_swap.assert_awaited_once_with("users", "shadow")
        manager._alias_swap.assert_not_called()
