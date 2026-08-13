"""Tests for embedding cache functionality."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.vector.embedding.cache import EmbeddingCache, InMemoryEmbeddingCache


class TestInMemoryEmbeddingCache:
    """Test InMemoryEmbeddingCache implementation."""

    @pytest.mark.asyncio
    async def test_cache_stores_embeddings(self):
        """Test that set() stores embeddings."""
        cache = InMemoryEmbeddingCache()
        embedding = [0.1, 0.2, 0.3]

        result = await cache.set("test text", embedding)

        assert result is True

    @pytest.mark.asyncio
    async def test_cache_retrieves_embeddings(self):
        """Test that get() retrieves stored embeddings."""
        cache = InMemoryEmbeddingCache()
        embedding = [0.1, 0.2, 0.3]

        await cache.set("test text", embedding)
        result = await cache.get("test text")

        assert result == embedding

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self):
        """Test that missing key returns None."""
        cache = InMemoryEmbeddingCache()

        result = await cache.get("nonexistent text")

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_eviction_lru(self):
        """Test that LRU eviction works when cache is full."""
        cache = InMemoryEmbeddingCache(max_size=2)

        await cache.set("text1", [0.1])
        await cache.set("text2", [0.2])
        assert await cache.get("text1") is not None

        await cache.set("text3", [0.3])

        assert await cache.get("text1") is None
        assert await cache.get("text2") == [0.2]
        assert await cache.get("text3") == [0.3]

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self):
        """Test that TTL is stored (simple verification)."""
        cache = InMemoryEmbeddingCache(ttl=3600)

        await cache.set("test", [0.1, 0.2])

        stats = await cache.get_stats()
        assert stats["ttl"] == 3600

    @pytest.mark.asyncio
    async def test_cache_with_model(self):
        """Test that cache works with model parameter."""
        cache = InMemoryEmbeddingCache()

        await cache.set("test text", [0.1, 0.2], model="gpt-4")
        result = await cache.get("test text", model="gpt-4")

        assert result == [0.1, 0.2]

    @pytest.mark.asyncio
    async def test_cache_different_models_separate(self):
        """Test that different models have separate cache entries."""
        cache = InMemoryEmbeddingCache()

        await cache.set("same text", [0.1], model="gpt-4")
        await cache.set("same text", [0.2], model="claude")

        result_gpt = await cache.get("same text", model="gpt-4")
        result_claude = await cache.get("same text", model="claude")

        assert result_gpt == [0.1]
        assert result_claude == [0.2]

    @pytest.mark.asyncio
    async def test_cache_delete(self):
        """Test deleting entries."""
        cache = InMemoryEmbeddingCache()

        await cache.set("test text", [0.1, 0.2])
        result = await cache.delete("test text")

        assert result is True
        assert await cache.get("test text") is None

    @pytest.mark.asyncio
    async def test_cache_clear_all(self):
        """Test clearing all entries."""
        cache = InMemoryEmbeddingCache()
        await cache.set("text1", [0.1])
        await cache.set("text2", [0.2])

        result = await cache.clear()

        assert result is True
        stats = await cache.get_stats()
        assert stats["size"] == 0

    @pytest.mark.asyncio
    async def test_cache_clear_by_model(self):
        """Test clearing entries for specific model."""
        cache = InMemoryEmbeddingCache()
        await cache.set("text1", [0.1], model="gpt-4")
        await cache.set("text2", [0.2], model="claude")
        await cache.set("text3", [0.3])

        result = await cache.clear("gpt-4")

        assert result is True
        assert await cache.get("text1", model="gpt-4") is None
        assert await cache.get("text2", model="claude") == [0.2]
        assert await cache.get("text3") == [0.3]

    @pytest.mark.asyncio
    async def test_cache_stats_tracking(self):
        """Test that cache stats are tracked correctly."""
        cache = InMemoryEmbeddingCache()

        await cache.get("miss1")
        await cache.set("hit1", [0.1])
        await cache.get("hit1")
        await cache.get("miss2")

        stats = await cache.get_stats()

        assert stats["hits"] == 1
        assert stats["misses"] == 2
        assert stats["size"] == 1


class TestEmbeddingCache:
    """Test EmbeddingCache wrapper around cache backend."""

    @pytest.mark.asyncio
    async def test_cache_uses_backend(self):
        """Test that cache wraps backend protocol correctly."""
        mock_backend = MagicMock()
        mock_backend.get = AsyncMock(return_value=[0.1, 0.2, 0.3])

        cache = EmbeddingCache(
            cache_service=mock_backend,
            ttl=3600,
            key_prefix="test:",
            enabled=True,
        )

        result = await cache.get("test text")

        assert result == [0.1, 0.2, 0.3]
        mock_backend.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_set_writes_to_backend(self):
        """Test that set() writes to backend."""
        mock_backend = MagicMock()
        mock_backend.set = AsyncMock(return_value=True)

        cache = EmbeddingCache(cache_service=mock_backend, ttl=1800)
        embedding = [0.1, 0.2, 0.3]

        result = await cache.set("test text", embedding)

        assert result is True
        mock_backend.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_get_miss(self):
        """Test get() returns None on cache miss."""
        mock_backend = MagicMock()
        mock_backend.get = AsyncMock(return_value=None)

        cache = EmbeddingCache(cache_service=mock_backend, enabled=True)

        result = await cache.get("test text")

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_disabled_returns_none(self):
        """Test that disabled cache returns None on get."""
        cache = EmbeddingCache(cache_service=None, enabled=False)

        result = await cache.get("test text")

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_disabled_returns_false_on_set(self):
        """Test that disabled cache returns False on set."""
        cache = EmbeddingCache(cache_service=None, enabled=False)

        result = await cache.set("test text", [0.1, 0.2])

        assert result is False

    @pytest.mark.asyncio
    async def test_cache_handles_backend_error(self):
        """Test that backend errors are handled gracefully."""
        mock_backend = MagicMock()
        mock_backend.get = AsyncMock(side_effect=OSError("Backend error"))

        cache = EmbeddingCache(cache_service=mock_backend, enabled=True)

        result = await cache.get("test text")

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_delete(self):
        """Test delete() calls backend."""
        mock_backend = MagicMock()
        mock_backend.delete = AsyncMock(return_value=True)

        cache = EmbeddingCache(cache_service=mock_backend, enabled=True)

        result = await cache.delete("test text")

        assert result is True
        mock_backend.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_clear_with_pattern(self):
        """Test clear() with backend that supports patterns."""
        mock_backend = MagicMock()
        mock_backend.clear_pattern = AsyncMock(return_value=True)

        cache = EmbeddingCache(
            cache_service=mock_backend,
            key_prefix="embed:",
            enabled=True,
        )

        result = await cache.clear("gpt-4")

        assert result is True
        mock_backend.clear_pattern.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_clear_without_pattern_support(self):
        """Test clear() with backend that doesn't support patterns."""
        mock_backend = MagicMock()
        if hasattr(mock_backend, "clear_pattern"):
            delattr(mock_backend, "clear_pattern")

        cache = EmbeddingCache(cache_service=mock_backend, enabled=True)

        result = await cache.clear()

        assert result is False

    @pytest.mark.asyncio
    async def test_cache_stats_with_backend(self):
        """Test get_stats() with backend stats support."""
        mock_backend = MagicMock()
        mock_backend.get_stats = AsyncMock(return_value={"hits": 10, "misses": 5})

        cache = EmbeddingCache(
            cache_service=mock_backend,
            ttl=1800,
            key_prefix="test:",
            enabled=True,
        )

        stats = await cache.get_stats()

        assert stats["enabled"] is True
        assert stats["ttl"] == 1800
        assert stats["cache_stats"]["hits"] == 10
