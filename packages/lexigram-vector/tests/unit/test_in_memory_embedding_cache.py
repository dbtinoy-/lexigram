"""InMemoryEmbeddingCache implementation tests."""

"""Embedding cache tests."""


from unittest.mock import MagicMock

import pytest

from lexigram.vector.embedding.cache import EmbeddingCache, InMemoryEmbeddingCache



class TestInMemoryEmbeddingCache:
    """Test InMemoryEmbeddingCache."""

    def test_init_default(self):
        """Test default initialization."""
        cache = InMemoryEmbeddingCache()

        assert cache.max_size == 1000
        assert cache.ttl == 86400
        assert cache.hits == 0
        assert cache.misses == 0
        assert len(cache._cache) == 0

    def test_init_custom(self):
        """Test custom initialization."""
        cache = InMemoryEmbeddingCache(max_size=500, ttl=3600)

        assert cache.max_size == 500
        assert cache.ttl == 3600

    def test_generate_key_without_model(self):
        """Test key generation without model."""
        cache = InMemoryEmbeddingCache()
        key = cache._generate_key("test text")

        assert len(key) == 16  # SHA256 hash truncated to 16 chars
        assert key.isalnum()

    def test_generate_key_with_model(self):
        """Test key generation with model."""
        cache = InMemoryEmbeddingCache()
        key = cache._generate_key("test text", "gpt-4")

        assert key.startswith("gpt-4:")
        assert len(key) > len("gpt-4:")

    @pytest.mark.asyncio
    async def test_get_cache_hit(self):
        """Test getting embedding from cache (hit)."""
        cache = InMemoryEmbeddingCache()
        embedding = [0.1, 0.2, 0.3]

        # Pre-populate cache
        await cache.set("test text", embedding)

        result = await cache.get("test text")

        assert result == embedding
        assert cache.hits == 1
        assert cache.misses == 0

    @pytest.mark.asyncio
    async def test_get_cache_miss(self):
        """Test getting embedding from cache (miss)."""
        cache = InMemoryEmbeddingCache()

        result = await cache.get("test text")

        assert result is None
        assert cache.hits == 0
        assert cache.misses == 1

    @pytest.mark.asyncio
    async def test_set_cache_success(self):
        """Test setting embedding in cache."""
        cache = InMemoryEmbeddingCache()
        embedding = [0.1, 0.2, 0.3]

        result = await cache.set("test text", embedding)

        assert result is True
        assert len(cache._cache) == 1
        assert cache.hits == 0
        assert cache.misses == 0

    @pytest.mark.asyncio
    async def test_set_cache_max_size(self):
        """Test setting embedding when at max size."""
        cache = InMemoryEmbeddingCache(max_size=2)

        # Fill cache to max
        await cache.set("text1", [0.1])
        await cache.set("text2", [0.2])
        assert len(cache._cache) == 2

        # Add one more - should evict oldest
        await cache.set("text3", [0.3])
        assert len(cache._cache) == 2

        # text1 should be gone, text2 and text3 should remain
        assert await cache.get("text1") is None
        assert await cache.get("text2") == [0.2]
        assert await cache.get("text3") == [0.3]

    @pytest.mark.asyncio
    async def test_delete_cache_success(self):
        """Test deleting embedding from cache."""
        cache = InMemoryEmbeddingCache()
        await cache.set("test text", [0.1, 0.2, 0.3])

        result = await cache.delete("test text")

        assert result is True
        assert len(cache._cache) == 0

    @pytest.mark.asyncio
    async def test_delete_cache_miss(self):
        """Test deleting non-existent embedding."""
        cache = InMemoryEmbeddingCache()

        result = await cache.delete("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_clear_cache_all(self):
        """Test clearing all cache entries."""
        cache = InMemoryEmbeddingCache()
        await cache.set("text1", [0.1])
        await cache.set("text2", [0.2])

        result = await cache.clear()

        assert result is True
        assert len(cache._cache) == 0

    @pytest.mark.asyncio
    async def test_clear_cache_by_model(self):
        """Test clearing cache entries for specific model."""
        cache = InMemoryEmbeddingCache()
        await cache.set("text1", [0.1], "gpt-4")
        await cache.set("text2", [0.2], "claude")
        await cache.set("text3", [0.3])  # No model

        result = await cache.clear("gpt-4")

        assert result is True
        assert len(cache._cache) == 2  # Should have claude and no-model entries
        assert await cache.get("text1", "gpt-4") is None
        assert await cache.get("text2", "claude") == [0.2]
        assert await cache.get("text3") == [0.3]

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test getting cache statistics."""
        cache = InMemoryEmbeddingCache(max_size=100, ttl=3600)

        # Generate some hits and misses
        await cache.get("miss1")  # miss
        await cache.set("hit1", [0.1])
        await cache.get("hit1")  # hit
        await cache.get("miss2")  # miss
        await cache.get("hit1")  # hit

        stats = await cache.get_stats()

        expected = {
            "enabled": True,
            "type": "in_memory",
            "size": 1,
            "max_size": 100,
            "hits": 2,
            "misses": 2,
            "hit_rate": "50.00%",
            "ttl": 3600,
        }
        assert stats == expected

    @pytest.mark.asyncio
    async def test_get_stats_empty_cache(self):
        """Test getting cache statistics for empty cache."""
        cache = InMemoryEmbeddingCache()

        stats = await cache.get_stats()

        expected = {
            "enabled": True,
            "type": "in_memory",
            "size": 0,
            "max_size": 1000,
            "hits": 0,
            "misses": 0,
            "hit_rate": "0.00%",
            "ttl": 86400,
        }
        assert stats == expected
