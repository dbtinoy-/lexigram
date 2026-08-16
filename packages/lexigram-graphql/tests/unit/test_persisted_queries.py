from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.graphql.core.persisted_queries import (
    APQHandler,
    APQResult,
    CacheBackendPersistedQueryStore,
    InMemoryPersistedQueryStore,
    RedisPersistedQueryStore,
    compute_query_hash,
    create_apq_handler,
)


class TestComputeQueryHash:
    def test_returns_hex_string(self) -> None:
        h = compute_query_hash("query { hello }")
        assert isinstance(h, str)
        assert len(h) > 0

    def test_deterministic(self) -> None:
        h1 = compute_query_hash("query { hello }")
        h2 = compute_query_hash("query { hello }")
        assert h1 == h2

    def test_different_queries_different_hashes(self) -> None:
        h1 = compute_query_hash("query { hello }")
        h2 = compute_query_hash("query { world }")
        assert h1 != h2


class TestInMemoryPersistedQueryStore:
    @pytest.mark.asyncio
    async def test_put_and_get(self) -> None:
        store = InMemoryPersistedQueryStore()
        await store.put("hash123", "query { hello }")
        result = await store.get("hash123")
        assert result == "query { hello }"

    @pytest.mark.asyncio
    async def test_get_missing(self) -> None:
        store = InMemoryPersistedQueryStore()
        result = await store.get("missing")
        assert result is None

    @pytest.mark.asyncio
    async def test_clear(self) -> None:
        store = InMemoryPersistedQueryStore()
        await store.put("h1", "q1")
        store.clear()
        result = await store.get("h1")
        assert result is None


class TestRedisPersistedQueryStore:
    @pytest.mark.asyncio
    async def test_get_missing(self) -> None:
        redis = AsyncMock()
        redis.get.return_value = None
        store = RedisPersistedQueryStore(redis_client=redis)
        result = await store.get("hash1")
        assert result is None
        redis.get.assert_awaited_once_with("graphql:apq:hash1")

    @pytest.mark.asyncio
    async def test_get_found(self) -> None:
        redis = AsyncMock()
        redis.get.return_value = b"query { hello }"
        store = RedisPersistedQueryStore(redis_client=redis)
        result = await store.get("hash1")
        assert result == "query { hello }"

    @pytest.mark.asyncio
    async def test_get_redis_error_returns_none(self) -> None:
        redis = AsyncMock()
        redis.get.side_effect = OSError("connection failed")
        store = RedisPersistedQueryStore(redis_client=redis)
        result = await store.get("hash1")
        assert result is None

    @pytest.mark.asyncio
    async def test_put(self) -> None:
        redis = AsyncMock()
        store = RedisPersistedQueryStore(redis_client=redis)
        await store.put("hash1", "query { hello }")
        redis.setex.assert_awaited_once_with("graphql:apq:hash1", 86400, "query { hello }")

    @pytest.mark.asyncio
    async def test_put_redis_error(self) -> None:
        redis = AsyncMock()
        redis.setex.side_effect = OSError("failed")
        store = RedisPersistedQueryStore(redis_client=redis)
        await store.put("hash1", "query")
        # Should not raise


class TestCacheBackendPersistedQueryStore:
    @pytest.mark.asyncio
    async def test_get(self) -> None:
        cache = MagicMock()
        cache.get = AsyncMock(return_value="query { hello }")
        store = CacheBackendPersistedQueryStore(cache=cache)
        result = await store.get("hash1")
        assert result == "query { hello }"
        cache.get.assert_awaited_once_with("graphql:apq:hash1")

    @pytest.mark.asyncio
    async def test_get_cache_error_returns_none(self) -> None:
        cache = MagicMock()
        cache.get = AsyncMock(side_effect=RuntimeError("fail"))
        store = CacheBackendPersistedQueryStore(cache=cache)
        result = await store.get("hash1")
        assert result is None

    @pytest.mark.asyncio
    async def test_put(self) -> None:
        cache = MagicMock()
        cache.set = AsyncMock()
        store = CacheBackendPersistedQueryStore(cache=cache)
        await store.put("hash1", "q")
        cache.set.assert_awaited_once_with("graphql:apq:hash1", "q", ttl=86400)

    @pytest.mark.asyncio
    async def test_put_cache_error(self) -> None:
        cache = MagicMock()
        cache.set = AsyncMock(side_effect=LookupError("fail"))
        store = CacheBackendPersistedQueryStore(cache=cache)
        await store.put("hash1", "q")
        # Should not raise


class TestAPQHandler:
    @pytest.mark.asyncio
    async def test_disabled_returns_query_as_is(self) -> None:
        store = InMemoryPersistedQueryStore()
        handler = APQHandler(store=store, enabled=False)
        result = await handler.resolve_query(query="{ hello }")
        assert result.query == "{ hello }"
        assert result.is_persisted is False

    @pytest.mark.asyncio
    async def test_no_query_no_apq_returns_empty(self) -> None:
        store = InMemoryPersistedQueryStore()
        handler = APQHandler(store=store, enabled=True)
        result = await handler.resolve_query(query=None)
        assert result.query is None
        assert result.is_persisted is False

    @pytest.mark.asyncio
    async def test_has_query_no_apq_stores_it(self) -> None:
        store = InMemoryPersistedQueryStore()
        handler = APQHandler(store=store, enabled=True)
        result = await handler.resolve_query(query="{ hello }")
        assert result.query == "{ hello }"
        assert result.is_persisted is False
        assert len(result.hash) > 0
        # Verify it was stored
        stored = await store.get(result.hash)
        assert stored == "{ hello }"

    @pytest.mark.asyncio
    async def test_apq_cache_hit(self) -> None:
        store = InMemoryPersistedQueryStore()
        await store.put("known_hash", "{ cached }")
        handler = APQHandler(store=store, enabled=True)
        result = await handler.resolve_query(
            query=None,
            extensions={"persistedQuery": {"sha256Hash": "known_hash", "version": 1}},
        )
        assert result.query == "{ cached }"
        assert result.is_persisted is True
        assert result.hash == "known_hash"

    @pytest.mark.asyncio
    async def test_apq_cache_miss_no_query(self) -> None:
        store = InMemoryPersistedQueryStore()
        handler = APQHandler(store=store, enabled=True)
        result = await handler.resolve_query(
            query=None,
            extensions={"persistedQuery": {"sha256Hash": "missing_hash", "version": 1}},
        )
        assert result.query is None
        assert result.is_persisted is False
        assert result.hash == "missing_hash"

    @pytest.mark.asyncio
    async def test_apq_cache_miss_with_query_stores_it(self) -> None:
        store = InMemoryPersistedQueryStore()
        handler = APQHandler(store=store, enabled=True)
        result = await handler.resolve_query(
            query="{ new query }",
            extensions={"persistedQuery": {"sha256Hash": "new_hash", "version": 1}},
        )
        assert result.query == "{ new query }"
        assert result.is_persisted is False
        # Verify it was stored
        stored = await store.get("new_hash")
        assert stored == "{ new query }"

    @pytest.mark.asyncio
    async def test_apq_extension_without_hash(self) -> None:
        store = InMemoryPersistedQueryStore()
        handler = APQHandler(store=store, enabled=True)
        result = await handler.resolve_query(
            query="{ hello }",
            extensions={"persistedQuery": {}},
        )
        assert result.query == "{ hello }"
        assert result.is_persisted is False

    @pytest.mark.asyncio
    async def test_enabled_property(self) -> None:
        handler = APQHandler(store=MagicMock(), enabled=True)
        assert handler.enabled is True
        handler2 = APQHandler(store=MagicMock(), enabled=False)
        assert handler2.enabled is False

    def test_create_extension_response(self) -> None:
        store = InMemoryPersistedQueryStore()
        handler = APQHandler(store=store)
        resp = handler.create_extension_response("abc123")
        assert resp == {
            "persistedQuery": {
                "sha256Hash": "abc123",
                "version": 1,
            },
        }


class TestCreateAPQHandler:
    def test_create_memory(self) -> None:
        handler = create_apq_handler(store_type="memory")
        assert isinstance(handler, APQHandler)
        assert isinstance(handler._store, InMemoryPersistedQueryStore)

    def test_create_redis_requires_kwargs(self) -> None:
        with pytest.raises(TypeError):
            create_apq_handler(store_type="redis")

    def test_unknown_store_type(self) -> None:
        with pytest.raises(ValueError, match="Unknown APQ store type"):
            create_apq_handler(store_type="invalid")
