"""Tests for caching utilities."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.search.exceptions import CacheError
from lexigram.search.lib.caching import (
    CacheConfig,
    CacheEntry,
    CacheManager,
    QueryCache,
    SearchCache,
    cache_context,
    cached,
)
from lexigram.search.types import SearchResponse


class TestCacheConfig:
    """Tests for CacheConfig."""

    def test_default_config(self) -> None:
        """Verify default cache config values."""
        config = CacheConfig()
        assert config.ttl_seconds == 300
        assert config.max_size == 1000
        assert config.cleanup_interval == 60
        assert config.enable_compression is False
        assert config.serializer == "json"


class TestCacheEntry:
    """Tests for CacheEntry."""

    def test_is_expired_no_ttl(self) -> None:
        """Verify entry without TTL never expires."""
        entry = CacheEntry(key="k", value="v", ttl_seconds=None)
        assert entry.is_expired is False

    def test_age_seconds(self) -> None:
        """Verify age_seconds returns positive value."""
        entry = CacheEntry(key="k", value="v", ttl_seconds=300)
        assert entry.age_seconds >= 0


class TestSearchCache:
    """Tests for SearchCache."""

    @pytest.fixture
    def cache(self) -> SearchCache:
        return SearchCache(config=CacheConfig(max_size=10, cleanup_interval=3600))

    @pytest.mark.asyncio
    async def test_start_stop(self, cache: SearchCache) -> None:
        """Verify start and stop lifecycle."""
        await cache.start()
        assert cache._running is True
        assert cache._cleanup_task is not None

        await cache.stop()
        assert cache._running is False

    @pytest.mark.asyncio
    async def test_start_idempotent(self, cache: SearchCache) -> None:
        """Verify calling start multiple times is safe."""
        await cache.start()
        task = cache._cleanup_task
        await cache.start()
        assert cache._cleanup_task is task

    @pytest.mark.asyncio
    async def test_stop_idempotent(self, cache: SearchCache) -> None:
        """Verify calling stop when not running is safe."""
        await cache.stop()  # Should not raise

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache: SearchCache) -> None:
        """Verify set and get roundtrip."""
        key = "test_key"
        value = {"data": "hello"}

        await cache.set(key, value)
        result = await cache.get(key)
        assert result == value

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, cache: SearchCache) -> None:
        """Verify get returns None for missing key."""
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_expired(self, cache: SearchCache) -> None:
        """Verify expired entry returns None and is removed."""
        from datetime import timedelta, timezone

        key = "expired_key"
        # Use ttl_seconds=1 (0 is falsy and gets replaced by default in set())
        await cache.set(key, "value", ttl_seconds=1)

        # Set created_at to the past so entry is expired
        entry = cache._cache[key]
        entry.created_at = datetime.now(timezone.utc) - timedelta(seconds=10)

        with patch('lexigram.search.lib.caching.ambient_clock.now', return_value=datetime.now(timezone.utc)):
            result = await cache.get(key)
            assert result is None
            assert key not in cache._cache

    @pytest.mark.asyncio
    async def test_delete_existing(self, cache: SearchCache) -> None:
        """Verify delete returns True for existing key."""
        await cache.set("key", "value")
        result = await cache.delete("key")
        assert result is True
        assert "key" not in cache._cache

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, cache: SearchCache) -> None:
        """Verify delete returns False for missing key."""
        result = await cache.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_clear(self, cache: SearchCache) -> None:
        """Verify clear removes all entries."""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.clear()
        assert len(cache._cache) == 0

    @pytest.mark.asyncio
    async def test_generate_key(self, cache: SearchCache) -> None:
        """Verify generate_key produces consistent keys."""
        with patch('lexigram.search.lib.caching.ambient_hashing') as mock_hashing:
            mock_hashing.digest.return_value = "mocked_hash"
            key1 = cache.generate_key("test")
            key2 = cache.generate_key("test")
            assert key1 == key2

    @pytest.mark.asyncio
    async def test_generate_key_differs_for_different_queries(self, cache: SearchCache) -> None:
        """Verify generate_key produces different keys."""
        with patch('lexigram.search.lib.caching.ambient_hashing') as mock_hashing:
            mock_hashing.digest.side_effect = lambda s: f"hash_{s}"
            key1 = cache.generate_key("query1")
            key2 = cache.generate_key("query2")
            assert key1 != key2

    @pytest.mark.asyncio
    async def test_evict_entries_empty(self, cache: SearchCache) -> None:
        """Verify evict on empty cache does nothing."""
        await cache._evict_entries()  # Should not raise

    @pytest.mark.asyncio
    async def test_evict_entries_removes_oldest(self) -> None:
        """Verify evict removes oldest entries."""
        big_cache = SearchCache(config=CacheConfig(max_size=100, cleanup_interval=3600))
        for i in range(20):
            await big_cache.set(f"key{i}", f"value{i}")

        assert len(big_cache._cache) == 20
        await big_cache._evict_entries()
        assert len(big_cache._cache) < 20
        assert len(big_cache._cache) == 18  # removed 2 (10% of 20)

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, cache: SearchCache) -> None:
        """Verify _cleanup_expired removes expired entries."""
        from datetime import timedelta, timezone

        await cache.set("fresh", "value", ttl_seconds=3600)
        await cache.set("stale", "value", ttl_seconds=1)

        # Manually set stale entry's created_at to the past
        stale_entry = cache._cache["stale"]
        stale_entry.created_at = datetime.now(timezone.utc) - timedelta(seconds=10)

        with patch('lexigram.search.lib.caching.ambient_clock.now', return_value=datetime.now(timezone.utc)):
            await cache._cleanup_expired()

        assert "fresh" in cache._cache
        assert "stale" not in cache._cache

    @pytest.mark.asyncio
    async def test_get_stats(self, cache: SearchCache) -> None:
        """Verify get_stats returns non-empty dict."""
        await cache.set("key", "value")
        stats = await cache.get_stats()
        assert stats["total_entries"] == 1
        assert stats["max_size"] == 10
        assert stats["hit_rate"] >= 0

    @pytest.mark.asyncio
    async def test_serialize_json(self, cache: SearchCache) -> None:
        """Verify JSON serialization."""
        result = await cache._serialize({"a": 1, "b": "hello"})
        assert isinstance(result, (str, bytes))

    @pytest.mark.asyncio
    async def test_serialize_pickle(self) -> None:
        """Verify pickle serialization."""
        cache = SearchCache(config=CacheConfig(serializer="pickle"))
        result = await cache._serialize({"a": 1})
        assert isinstance(result, bytes)

    @pytest.mark.asyncio
    async def test_serialize_unsupported(self, cache: SearchCache) -> None:
        """Verify unsupported serializer raises."""
        cache = SearchCache(config=CacheConfig(serializer="xml"))
        with pytest.raises(CacheError, match="Unsupported serializer: xml"):
            await cache._serialize("value")

    @pytest.mark.asyncio
    async def test_deserialize_unsupported(self, cache: SearchCache) -> None:
        """Verify unsupported deserializer raises."""
        cache = SearchCache(config=CacheConfig(serializer="xml"))
        with pytest.raises(CacheError, match="Unsupported serializer: xml"):
            await cache._deserialize("value")

    @pytest.mark.asyncio
    async def test_set_evicts_when_full(self, cache: SearchCache) -> None:
        """Verify set triggers eviction when at capacity."""
        small_cache = SearchCache(config=CacheConfig(max_size=2))
        await small_cache.set("key1", "value1")
        await small_cache.set("key2", "value2")
        await small_cache.set("key3", "value3")
        assert len(small_cache._cache) <= 2

    @pytest.mark.asyncio
    async def test_get_updates_access_stats(self, cache: SearchCache) -> None:
        """Verify get updates access count and time."""
        await cache.set("key", "value")
        entry_before = cache._cache["key"]
        assert entry_before.access_count == 0

        await cache.get("key")
        assert cache._cache["key"].access_count == 1


class TestQueryCache:
    """Tests for QueryCache."""

    @pytest.fixture
    def search_cache(self) -> SearchCache:
        return SearchCache()

    @pytest.fixture
    def query_cache(self, search_cache: SearchCache) -> QueryCache:
        return QueryCache(cache=search_cache)

    @pytest.mark.asyncio
    async def test_get_search_results_missing(
        self, query_cache: QueryCache,
    ) -> None:
        """Verify get_search_results returns None for missing query."""
        with patch('lexigram.search.lib.caching.ambient_hashing') as mock_hashing:
            mock_hashing.digest.return_value = "some_key"
            result = await query_cache.get_search_results("test query")
            assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get_search_results(
        self, query_cache: QueryCache,
    ) -> None:
        """Verify set and get roundtrip for search results."""
        response = SearchResponse(
            results=[],
            total=0,
            page=1,
            per_page=20,
            query="test",
            took_ms=1,
        )

        with patch('lexigram.search.lib.caching.ambient_hashing') as mock_hashing:
            mock_hashing.digest.side_effect = ["key1", "key1"]
            await query_cache.set_search_results("test query", response)
            cached = await query_cache.get_search_results("test query")
            assert cached is not None

    @pytest.mark.asyncio
    async def test_invalidate_query(
        self, query_cache: QueryCache,
    ) -> None:
        """Verify invalidate_query removes cached result."""
        response = SearchResponse(
            results=[],
            total=0,
            page=1,
            per_page=20,
            query="test",
            took_ms=1,
        )

        with patch('lexigram.search.lib.caching.ambient_hashing') as mock_hashing:
            mock_hashing.digest.side_effect = ["key1", "key1", "key1"]
            await query_cache.set_search_results("test query", response)
            await query_cache.invalidate_query("test query")
            result = await query_cache.get_search_results("test query")
            assert result is None

    @pytest.mark.asyncio
    async def test_invalidate_by_pattern(
        self, query_cache: QueryCache,
    ) -> None:
        """Verify invalidate_by_pattern removes matching entries."""
        with patch('lexigram.search.lib.caching.ambient_hashing') as mock_hashing:
            mock_hashing.digest.side_effect = lambda q, **kw: q
            with patch.object(query_cache.cache, 'generate_key', side_effect=lambda q, **kw: q):
                await query_cache.cache.set("query1", "value1")
                await query_cache.cache.set("query2", "value2")
                await query_cache.cache.set("other", "value3")

                invalidated = await query_cache.invalidate_by_pattern("query.*")
                assert invalidated == 2


class TestCacheManager:
    """Tests for CacheManager."""

    @pytest.fixture
    def manager(self) -> CacheManager:
        return CacheManager()

    def test_create_cache(self, manager: CacheManager) -> None:
        """Verify create_cache creates and registers a cache."""
        cache = manager.create_cache("default")
        assert "default" in manager.caches
        assert "default" in manager.query_caches
        assert isinstance(cache, SearchCache)

    def test_create_duplicate_cache_raises(self, manager: CacheManager) -> None:
        """Verify creating duplicate cache raises."""
        manager.create_cache("default")
        with pytest.raises(CacheError, match="Cache 'default' already exists"):
            manager.create_cache("default")

    def test_get_cache(self, manager: CacheManager) -> None:
        """Verify get_cache returns the cache."""
        manager.create_cache("default")
        cache = manager.get_cache("default")
        assert isinstance(cache, SearchCache)

    def test_get_nonexistent_cache_raises(self, manager: CacheManager) -> None:
        """Verify get_cache for missing cache raises."""
        with pytest.raises(CacheError, match="Cache 'nonexistent' not found"):
            manager.get_cache("nonexistent")

    def test_get_query_cache(self, manager: CacheManager) -> None:
        """Verify get_query_cache returns query cache."""
        manager.create_cache("default")
        qcache = manager.get_query_cache("default")
        assert isinstance(qcache, QueryCache)

    def test_get_nonexistent_query_cache_raises(self, manager: CacheManager) -> None:
        """Verify get_query_cache for missing cache raises."""
        with pytest.raises(CacheError, match="Query cache 'nonexistent' not found"):
            manager.get_query_cache("nonexistent")

    @pytest.mark.asyncio
    async def test_start_all(self, manager: CacheManager) -> None:
        """Verify start_all starts all caches."""
        cache1 = SearchCache()
        cache2 = SearchCache()
        manager.caches["a"] = cache1
        manager.caches["b"] = cache2

        with patch.object(cache1, 'start', new_callable=AsyncMock) as mock1:
            with patch.object(cache2, 'start', new_callable=AsyncMock) as mock2:
                await manager.start_all()
                mock1.assert_awaited_once()
                mock2.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stop_all(self, manager: CacheManager) -> None:
        """Verify stop_all stops all caches."""
        cache1 = SearchCache()
        cache2 = SearchCache()
        manager.caches["a"] = cache1
        manager.caches["b"] = cache2

        with patch.object(cache1, 'stop', new_callable=AsyncMock) as mock1:
            with patch.object(cache2, 'stop', new_callable=AsyncMock) as mock2:
                await manager.stop_all()
                mock1.assert_awaited_once()
                mock2.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_clear_all(self, manager: CacheManager) -> None:
        """Verify clear_all clears all caches."""
        cache1 = SearchCache()
        cache2 = SearchCache()
        manager.caches["a"] = cache1
        manager.caches["b"] = cache2

        with patch.object(cache1, 'clear', new_callable=AsyncMock) as mock1:
            with patch.object(cache2, 'clear', new_callable=AsyncMock) as mock2:
                await manager.clear_all()
                mock1.assert_awaited_once()
                mock2.assert_awaited_once()


class TestCacheContext:
    """Tests for cache_context."""

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Verify cache_context starts and stops the cache."""
        mock_cache = MagicMock()
        mock_cache.start = AsyncMock()
        mock_cache.stop = AsyncMock()

        async with cache_context(mock_cache) as cache:
            assert cache is mock_cache

        mock_cache.start.assert_awaited_once()
        mock_cache.stop.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_context_manager_stops_on_error(self) -> None:
        """Verify cache_context stops on error."""
        mock_cache = MagicMock()
        mock_cache.start = AsyncMock()
        mock_cache.stop = AsyncMock()

        with pytest.raises(RuntimeError):
            async with cache_context(mock_cache):
                raise RuntimeError("boom")

        mock_cache.start.assert_awaited_once()
        mock_cache.stop.assert_awaited_once()


class TestCachedDecorator:
    """Tests for the cached decorator."""

    @pytest.mark.asyncio
    async def test_cached_decorator_caches_result(self) -> None:
        """Verify cached decorator caches function results."""
        stored: dict[str, str] = {}
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(side_effect=lambda k: stored.get(k))
        mock_cache.set = AsyncMock(side_effect=lambda *args: stored.update({args[0]: args[1]}))

        call_count = 0

        with patch('lexigram.search.lib.caching.ambient_hashing') as mock_hashing:
            mock_hashing.digest.return_value = "key"

            @cached(mock_cache, ttl_seconds=60)
            async def my_func(arg: str) -> str:
                nonlocal call_count
                call_count += 1
                return f"result_{arg}"

            result1 = await my_func("hello")
            result2 = await my_func("hello")

        assert result1 == "result_hello"
        assert result2 == "result_hello"
        assert call_count == 1
        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_cached_decorator_hits_cache(self) -> None:
        """Verify cached decorator returns cached value."""
        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(return_value="cached_result")
        mock_cache.set = AsyncMock()

        call_count = 0

        with patch('lexigram.search.lib.caching.ambient_hashing') as mock_hashing:
            mock_hashing.digest.return_value = "key"

            @cached(mock_cache)
            async def my_func() -> str:
                nonlocal call_count
                call_count += 1
                return "fresh_result"

            result = await my_func()

        assert result == "cached_result"
        assert call_count == 0
        mock_cache.set.assert_not_called()
