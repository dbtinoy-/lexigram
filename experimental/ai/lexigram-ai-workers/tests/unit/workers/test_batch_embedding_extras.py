"""Unit tests for batch embedding cache and progress."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.workers.batch_embedding.cache import EmbeddingCache
from lexigram.ai.workers.batch_embedding.progress import ProgressTracker
from lexigram.ai.workers.batch_embedding.types import EmbeddingStatus

class TestEmbeddingCache:
    @pytest.mark.asyncio
    async def test_cache_get_set(self) -> None:
        cache = EmbeddingCache()
        await cache.set("hello", "model-1", [0.1, 0.2])
        emb = await cache.get("hello", "model-1")
        assert emb == [0.1, 0.2]
        
        assert await cache.get("world", "model-1") is None
        assert cache.size() == 1

    @pytest.mark.asyncio
    async def test_cache_batch(self) -> None:
        cache = EmbeddingCache()
        await cache.set_batch([("hello", [0.1]), ("world", [0.2])], "model-1")
        
        embs, uncached = await cache.get_batch(["hello", "test", "world"], "model-1")
        assert embs[0] == [0.1]
        assert embs[1] is None
        assert embs[2] == [0.2]
        assert len(uncached) == 1
        assert uncached[0] == (1, "test")

    @pytest.mark.asyncio
    async def test_clear(self) -> None:
        cache = EmbeddingCache()
        await cache.set("hello", "model-1", [0.1])
        await cache.clear()
        assert cache.size() == 0

    @pytest.mark.asyncio
    async def test_get_embeddings_with_cache(self) -> None:
        cache = EmbeddingCache()
        await cache.set("hello", "model-1", [0.1])
        
        provider = MagicMock()
        provider.embed_texts = AsyncMock(return_value=[[0.2], [0.3]])
        
        embs, hits, misses = await cache.get_embeddings_with_cache(
            ["hello", "world", "test"], "model-1", provider
        )
        assert hits == 1
        assert misses == 2
        assert embs == [[0.1], [0.2], [0.3]]
        
        # Check cache was updated
        assert await cache.get("world", "model-1") == [0.2]

class TestBatchEmbeddingProgressTracker:
    @pytest.mark.asyncio
    async def test_tracker(self) -> None:
        tracker = ProgressTracker()
        await tracker.initialize_job("job1", total_texts=10)
        
        p = await tracker.get_progress("job1")
        assert p is not None
        assert p.total_texts == 10
        assert p.status == EmbeddingStatus.PENDING

        await tracker.update_progress("job1", status=EmbeddingStatus.PROCESSING, texts_processed=5)
        p2 = await tracker.get_progress("job1")
        assert p2 is not None
        assert p2.texts_processed == 5
        
        active = tracker.get_active_jobs()
        assert "job1" in active

        stats = tracker.get_stats()
        assert stats["active_jobs"] == 1
        
        await tracker.remove_job("job1")
        assert await tracker.get_progress("job1") is None
