"""Tests for embedding cache functionality."""

from unittest.mock import MagicMock

import pytest

from lexigram.vector.embedding.cache import EmbeddingCache, InMemoryEmbeddingCache


class TestEmbeddingCache:
    """Test EmbeddingCache with external cache service."""

    def test_init_with_cache_service(self):
        """Test initialization with cache service."""
        mock_cache = MagicMock()
        cache = EmbeddingCache(
            cache_service=mock_cache,
            ttl=3600,
            key_prefix="test:",
            enabled=True,
        )

        assert cache.cache_service == mock_cache
        assert cache.ttl == 3600
        assert cache.key_prefix == "test:"
        assert cache.enabled is True

    def test_init_without_cache_service(self):
        """Test initialization without cache service."""
        cache = EmbeddingCache(cache_service=None, enabled=True)

        assert cache.cache_service is None
        assert cache.enabled is False

    def test_init_disabled(self):
        """Test initialization with caching disabled."""
        mock_cache = MagicMock()
        cache = EmbeddingCache(cache_service=mock_cache, enabled=False)

        assert cache.enabled is False

    def test_generate_key_without_model(self):
        """Test key generation without model."""
        cache = EmbeddingCache(cache_service=MagicMock(), key_prefix="embed:")
        key = cache._generate_key("test text")

        assert key.startswith("embed:")
        assert len(key) > len("embed:")  # Should have hash

    def test_generate_key_with_model(self):
        """Test key generation with model."""
        cache = EmbeddingCache(cache_service=MagicMock(), key_prefix="embed:")
        key = cache._generate_key("test text", "gpt-4")

        assert key.startswith("embed:")
        assert "gpt-4:" in key

    @pytest.mark.asyncio
    async def test_get_cache_hit(self):
        """Test getting embedding from cache (hit)."""
        mock_cache = MagicMock()

        async def get_side_effect(*args, **kwargs):
            return [0.1, 0.2, 0.3]

        mock_cache.get = MagicMock(side_effect=get_side_effect)

        cache = EmbeddingCache(cache_service=mock_cache)
        result = await cache.get("test text")

        assert result == [0.1, 0.2, 0.3]
        mock_cache.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cache_miss(self):
        """Test getting embedding from cache (miss)."""
        mock_cache = MagicMock()

        async def get_side_effect(*args, **kwargs):
            return None

        mock_cache.get = MagicMock(side_effect=get_side_effect)

        cache = EmbeddingCache(cache_service=mock_cache)
        result = await cache.get("test text")

        assert result is None
        mock_cache.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cache_disabled(self):
        """Test getting embedding when cache is disabled."""
        cache = EmbeddingCache(cache_service=None, enabled=False)
        result = await cache.get("test text")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_cache_error(self):
        """Test getting embedding when cache throws error."""
        mock_cache = MagicMock()

        async def get_side_effect(*args, **kwargs):
            raise OSError("Cache error")

        mock_cache.get = MagicMock(side_effect=get_side_effect)

        cache = EmbeddingCache(cache_service=mock_cache)
        result = await cache.get("test text")

        assert result is None
        mock_cache.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_cache_success(self):
        """Test setting embedding in cache."""
        mock_cache = MagicMock()

        async def set_side_effect(*args, **kwargs):
            return None

        mock_cache.set = MagicMock(side_effect=set_side_effect)
        embedding = [0.1, 0.2, 0.3]

        cache = EmbeddingCache(cache_service=mock_cache, ttl=1800)
        result = await cache.set("test text", embedding)

        assert result is True
        mock_cache.set.assert_called_once_with(
            cache._generate_key("test text"),
            embedding,
            ttl=1800,
        )

    @pytest.mark.asyncio
    async def test_set_cache_disabled(self):
        """Test setting embedding when cache is disabled."""
        cache = EmbeddingCache(cache_service=None, enabled=False)
        result = await cache.set("test text", [0.1, 0.2, 0.3])

        assert result is False

    @pytest.mark.asyncio
    async def test_set_cache_error(self):
        """Test setting embedding when cache throws error."""
        mock_cache = MagicMock()

        async def set_side_effect(*args, **kwargs):
            raise OSError("Cache error")

        mock_cache.set = MagicMock(side_effect=set_side_effect)

        cache = EmbeddingCache(cache_service=mock_cache)
        result = await cache.set("test text", [0.1, 0.2, 0.3])

        assert result is False

    @pytest.mark.asyncio
    async def test_set_with_custom_ttl(self):
        """Test setting embedding with custom TTL."""
        mock_cache = MagicMock()

        async def set_side_effect(*args, **kwargs):
            return None

        mock_cache.set = MagicMock(side_effect=set_side_effect)
        embedding = [0.1, 0.2, 0.3]

        cache = EmbeddingCache(cache_service=mock_cache, ttl=3600)
        result = await cache.set("test text", embedding, ttl=7200)

        assert result is True
        mock_cache.set.assert_called_once_with(
            cache._generate_key("test text"),
            embedding,
            ttl=7200,
        )

    @pytest.mark.asyncio
    async def test_delete_cache_success(self):
        """Test deleting embedding from cache."""
        mock_cache = MagicMock()

        async def delete_side_effect(*args, **kwargs):
            return None

        mock_cache.delete = MagicMock(side_effect=delete_side_effect)

        cache = EmbeddingCache(cache_service=mock_cache)
        result = await cache.delete("test text")

        assert result is True
        mock_cache.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_cache_disabled(self):
        """Test deleting embedding when cache is disabled."""
        cache = EmbeddingCache(cache_service=None, enabled=False)
        result = await cache.delete("test text")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_cache_error(self):
        """Test deleting embedding when cache throws error."""
        mock_cache = MagicMock()

        async def delete_side_effect(*args, **kwargs):
            raise OSError("Cache error")

        mock_cache.delete = MagicMock(side_effect=delete_side_effect)

        cache = EmbeddingCache(cache_service=mock_cache)
        result = await cache.delete("test text")

        assert result is False

    @pytest.mark.asyncio
    async def test_clear_cache_with_pattern_support(self):
        """Test clearing cache with pattern support."""
        mock_cache = MagicMock()

        async def clear_pattern_side_effect(*args, **kwargs):
            return None

        mock_cache.clear_pattern = MagicMock(side_effect=clear_pattern_side_effect)

        cache = EmbeddingCache(cache_service=mock_cache, key_prefix="embed:")
        result = await cache.clear("gpt-4")

        assert result is True
        mock_cache.clear_pattern.assert_called_once_with("embed:gpt-4:*")

    @pytest.mark.asyncio
    async def test_clear_cache_without_pattern_support(self):
        """Test clearing cache without pattern support."""
        mock_cache = (
            MagicMock()
        )  # Use MagicMock instead of AsyncMock to avoid auto-mocking
        # Explicitly remove clear_pattern method
        if hasattr(mock_cache, "clear_pattern"):
            delattr(mock_cache, "clear_pattern")

        cache = EmbeddingCache(cache_service=mock_cache)
        result = await cache.clear()

        assert result is False

    @pytest.mark.asyncio
    async def test_clear_cache_disabled(self):
        """Test clearing cache when disabled."""
        cache = EmbeddingCache(cache_service=None, enabled=False)
        result = await cache.clear()

        assert result is False

    @pytest.mark.asyncio
    async def test_clear_cache_error(self):
        """Test clearing cache when error occurs."""
        mock_cache = MagicMock()

        async def clear_pattern_side_effect(*args, **kwargs):
            raise OSError("Cache error")

        mock_cache.clear_pattern = MagicMock(side_effect=clear_pattern_side_effect)

        cache = EmbeddingCache(cache_service=mock_cache)
        result = await cache.clear()

        assert result is False

    @pytest.mark.asyncio
    async def test_get_stats_with_stats_support(self):
        """Test getting cache stats with stats support."""
        mock_cache = MagicMock()

        async def get_stats_side_effect(*args, **kwargs):
            return {"hits": 10, "misses": 5}

        mock_cache.get_stats = MagicMock(side_effect=get_stats_side_effect)

        cache = EmbeddingCache(cache_service=mock_cache, ttl=1800, key_prefix="test:")
        stats = await cache.get_stats()

        expected = {
            "enabled": True,
            "ttl": 1800,
            "key_prefix": "test:",
            "cache_stats": {"hits": 10, "misses": 5},
        }
        assert stats == expected

    @pytest.mark.asyncio
    async def test_get_stats_without_stats_support(self):
        """Test getting cache stats without stats support."""
        mock_cache = MagicMock()  # Use MagicMock instead of AsyncMock
        # Explicitly remove get_stats method
        if hasattr(mock_cache, "get_stats"):
            delattr(mock_cache, "get_stats")

        cache = EmbeddingCache(cache_service=mock_cache)
        stats = await cache.get_stats()

        expected = {
            "enabled": True,
            "ttl": 86400,
            "key_prefix": "embedding:",
            "message": "Cache service does not provide stats",
        }
        assert stats == expected

    @pytest.mark.asyncio
    async def test_get_stats_disabled(self):
        """Test getting cache stats when disabled."""
        cache = EmbeddingCache(cache_service=None, enabled=False)
        stats = await cache.get_stats()

        expected = {
            "enabled": False,
            "message": "Caching disabled",
        }
        assert stats == expected

    @pytest.mark.asyncio
    async def test_get_stats_error(self):
        """Test getting cache stats when error occurs."""
        mock_cache = MagicMock()

        async def get_stats_side_effect(*args, **kwargs):
            raise OSError("Stats error")

        mock_cache.get_stats = MagicMock(side_effect=get_stats_side_effect)

        cache = EmbeddingCache(cache_service=mock_cache)
        stats = await cache.get_stats()

        assert stats["enabled"] is True
        assert "error" in stats


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
