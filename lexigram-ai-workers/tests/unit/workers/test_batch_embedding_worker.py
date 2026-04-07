"""Unit tests for lexigram.ai.workers.batch_embedding.worker."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from lexigram.result import Ok

from lexigram.ai.workers.batch_embedding.types import (
    BatchEmbeddingResult,
    EmbeddingStatus,
)
from lexigram.ai.workers.batch_embedding.worker import BatchEmbeddingWorker
from lexigram.contracts.ai.rag import ChunkProtocol


@dataclass(slots=True)
class _TestChunk:
    text: str
    metadata: dict[str, Any] | None = None
    score: float | None = None


class TestBatchEmbeddingWorker:
    @pytest.fixture
    def queue(self) -> MagicMock:
        q = MagicMock()
        q.enqueue = AsyncMock(return_value=Ok("job-123"))
        return q

    @pytest.fixture
    def provider(self) -> MagicMock:
        p = MagicMock()
        p.embed_texts = AsyncMock(return_value=[[0.1], [0.2]])
        return p

    @pytest.fixture
    def store(self) -> MagicMock:
        s = MagicMock()
        s.add_texts = AsyncMock()
        return s

    @pytest.fixture
    def worker(self, store, provider, queue) -> BatchEmbeddingWorker:
        return BatchEmbeddingWorker(
            vector_store=store,
            embedding_provider=provider,
            queue=queue,
            concurrency=1,
            enable_cache=True,
        )

    @pytest.mark.asyncio
    async def test_embed_batch(self, worker: BatchEmbeddingWorker, queue: MagicMock) -> None:
        chunks: list[ChunkProtocol] = [
            _TestChunk(text="hello", metadata={"chunk_index": 0})
        ]
        job_id = await worker.embed_batch(chunks, "coll")
        
        queue.enqueue.assert_awaited_once()
        assert job_id == "job-123"
        prog = await worker.get_progress("job-123")
        assert prog.total_texts == 1
        assert prog.status == EmbeddingStatus.PENDING

    @pytest.mark.asyncio
    @patch("lexigram.di.resolution.context.get_resolver")
    async def test_start_stop(self, mock_get_resolver, worker: BatchEmbeddingWorker) -> None:
        # Create a mock resolver that returns a mock TaskWorkerClass
        mock_worker_instance = MagicMock()
        mock_worker_instance.start = AsyncMock()
        mock_worker_instance.stop = AsyncMock()
        
        mock_class = MagicMock(return_value=mock_worker_instance)
        
        mock_resolver = AsyncMock()
        mock_resolver.resolve = AsyncMock(return_value=mock_class)
        mock_get_resolver.return_value = mock_resolver
        
        await worker.start()
        assert worker._running is True
        assert len(worker._workers) == 1
        mock_worker_instance.start.assert_awaited_once()

        await worker.stop()
        assert worker._running is False
        assert len(worker._workers) == 0
        mock_worker_instance.stop.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handle_batch_embed_success(self, worker: BatchEmbeddingWorker, provider: MagicMock, store: MagicMock) -> None:
        chunks_data = [{"text": "hello", "metadata": {}}, {"text": "world", "metadata": {}}]
        
        # Pre-initialize progress tracker so it updates the actual job status
        await worker._progress_tracker.initialize_job("job-1", total_texts=2)

        res = await worker._handle_batch_embed(
            chunks=chunks_data,
            collection_name="coll",
            model_name="m1",
            batch_size=10,
            use_cache=False,
        )
        
        assert isinstance(res, BatchEmbeddingResult)
        assert res.success is True
        assert res.embeddings_generated == 2
        provider.embed_texts.assert_awaited()
        store.add_texts.assert_awaited()

    @pytest.mark.asyncio
    async def test_handle_batch_embed_failure(self, worker: BatchEmbeddingWorker, provider: MagicMock) -> None:
        chunks_data = [{"text": "hello"}]
        provider.embed_texts.side_effect = Exception("API error")
        
        res = await worker._handle_batch_embed(
            chunks=chunks_data,
            collection_name="coll",
            model_name="m1",
            batch_size=10,
            use_cache=False,
        )
        assert res.success is False
        assert "API error" in res.error

    def test_get_stats(self, worker: BatchEmbeddingWorker) -> None:
        stats = worker.get_stats()
        assert stats["worker_id"] == "batch-embedding"
        assert stats["running"] is False
        assert "active_jobs" in stats

    @pytest.mark.asyncio
    async def test_clear_cache(self, worker: BatchEmbeddingWorker) -> None:
        await worker._cache.set("txt", "model", [0.1])
        assert worker._cache.size() == 1
        await worker.clear_cache()
        assert worker._cache.size() == 0
