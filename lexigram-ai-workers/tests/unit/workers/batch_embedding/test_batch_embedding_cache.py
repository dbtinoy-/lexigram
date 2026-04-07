"""Tests for batch embedding cache."""

from __future__ import annotations

import pytest

from lexigram.ai.workers.batch_embedding.cache import EmbeddingCache


@pytest.fixture
def cache() -> EmbeddingCache:
    """Create an EmbeddingCache instance."""
    return EmbeddingCache()


class TestEmbeddingCache:
    """Test EmbeddingCache class."""

    @pytest.mark.asyncio
    async def test_get_missing_returns_none(self, cache: EmbeddingCache) -> None:
        """Test getting a missing key returns None."""
        result = await cache.get("hello", "ada-002")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache: EmbeddingCache) -> None:
        """Test setting and getting a value."""
        await cache.set("hello", "ada-002", [0.1, 0.2, 0.3])
        result = await cache.get("hello", "ada-002")
        assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_get_different_model(self, cache: EmbeddingCache) -> None:
        """Test getting with different model returns None."""
        await cache.set("hello", "model-a", [0.1, 0.2])
        result = await cache.get("hello", "model-b")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_batch_all_cached(self, cache: EmbeddingCache) -> None:
        """Test get_batch returns all cached embeddings."""
        await cache.set("hello", "ada-002", [0.1])
        await cache.set("world", "ada-002", [0.2])

        cached, uncached = await cache.get_batch(["hello", "world"], "ada-002")
        assert cached == [[0.1], [0.2]]
        assert uncached == []

    @pytest.mark.asyncio
    async def test_get_batch_partial_cache(self, cache: EmbeddingCache) -> None:
        """Test get_batch with some cached and some not."""
        await cache.set("hello", "ada-002", [0.1])

        cached, uncached = await cache.get_batch(["hello", "world"], "ada-002")
        assert cached[0] == [0.1]
        assert cached[1] is None
        assert uncached == [(1, "world")]

    @pytest.mark.asyncio
    async def test_get_batch_none_cached(self, cache: EmbeddingCache) -> None:
        """Test get_batch returns all as uncached."""
        cached, uncached = await cache.get_batch(["hello", "world"], "ada-002")
        assert cached == [None, None]
        assert uncached == [(0, "hello"), (1, "world")]

    @pytest.mark.asyncio
    async def test_set_batch(self, cache: EmbeddingCache) -> None:
        """Test setting multiple embeddings at once."""
        await cache.set_batch(
            [("hello", [0.1]), ("world", [0.2])],
            "ada-002",
        )
        result1 = await cache.get("hello", "ada-002")
        result2 = await cache.get("world", "ada-002")
        assert result1 == [0.1]
        assert result2 == [0.2]

    @pytest.mark.asyncio
    async def test_clear(self, cache: EmbeddingCache) -> None:
        """Test clearing the cache."""
        await cache.set("hello", "ada-002", [0.1])
        await cache.clear()
        result = await cache.get("hello", "ada-002")
        assert result is None

    def test_size_empty(self, cache: EmbeddingCache) -> None:
        """Test size returns 0 for empty cache."""
        assert cache.size() == 0

    @pytest.mark.asyncio
    async def test_size_after_set(self, cache: EmbeddingCache) -> None:
        """Test size returns correct count."""
        await cache.set("hello", "ada-002", [0.1])
        await cache.set("world", "ada-002", [0.2])
        await cache.set("different", "model-b", [0.3])
        assert cache.size() == 3

    @pytest.mark.asyncio
    async def test_get_embeddings_with_cache_all_hits(self, cache: EmbeddingCache) -> None:
        """Test get_embeddings_with_cache when all are cached."""
        await cache.set("hello", "ada-002", [0.1, 0.2])
        await cache.set("world", "ada-002", [0.3, 0.4])

        class MockProvider:
            async def embed_texts(self, texts):
                return [[1.0, 1.0], [2.0, 2.0]]

        embeddings, hits, misses = await cache.get_embeddings_with_cache(
            ["hello", "world"], "ada-002", MockProvider()
        )
        assert embeddings == [[0.1, 0.2], [0.3, 0.4]]
        assert hits == 2
        assert misses == 0

    @pytest.mark.asyncio
    async def test_get_embeddings_with_cache_all_misses(self, cache: EmbeddingCache) -> None:
        """Test get_embeddings_with_cache when none are cached."""

        class MockProvider:
            async def embed_texts(self, texts):
                return [[0.1, 0.2], [0.3, 0.4]]

        embeddings, hits, misses = await cache.get_embeddings_with_cache(
            ["hello", "world"], "ada-002", MockProvider()
        )
        assert embeddings == [[0.1, 0.2], [0.3, 0.4]]
        assert hits == 0
        assert misses == 2

    @pytest.mark.asyncio
    async def test_get_embeddings_with_cache_partial(self, cache: EmbeddingCache) -> None:
        """Test get_embeddings_with_cache with partial cache hits."""
        await cache.set("hello", "ada-002", [0.1, 0.2])

        class MockProvider:
            async def embed_texts(self, texts):
                return [[0.3, 0.4]]

        embeddings, hits, misses = await cache.get_embeddings_with_cache(
            ["hello", "world"], "ada-002", MockProvider()
        )
        assert embeddings == [[0.1, 0.2], [0.3, 0.4]]
        assert hits == 1
        assert misses == 1

    @pytest.mark.asyncio
    async def test_concurrent_access(self, cache: EmbeddingCache) -> None:
        """Test concurrent access to cache is thread-safe."""
        import asyncio

        async def write(i: int):
            await cache.set(f"text-{i}", "ada-002", [float(i)])

        async def read(i: int):
            return await cache.get(f"text-{i}", "ada-002")

        await asyncio.gather(*[write(i) for i in range(10)])
        results = await asyncio.gather(*[read(i) for i in range(10)])
        assert all(r is not None for r in results)


class TestEmbeddingCacheKeyUniqueness:
    """Test cache key uniqueness."""

    @pytest.mark.asyncio
    async def test_same_text_different_models(self, cache: EmbeddingCache) -> None:
        """Test same text with different models uses different keys."""
        await cache.set("hello", "model-a", [0.1])
        await cache.set("hello", "model-b", [0.2])

        result_a = await cache.get("hello", "model-a")
        result_b = await cache.get("hello", "model-b")
        assert result_a == [0.1]
        assert result_b == [0.2]

    @pytest.mark.asyncio
    async def test_hash_collision_handling(self, cache: EmbeddingCache) -> None:
        """Test that different texts don't share cache entries."""
        await cache.set("text1", "ada-002", [0.1])
        await cache.set("text2", "ada-002", [0.2])

        result1 = await cache.get("text1", "ada-002")
        result2 = await cache.get("text2", "ada-002")
        assert result1 == [0.1]
        assert result2 == [0.2]