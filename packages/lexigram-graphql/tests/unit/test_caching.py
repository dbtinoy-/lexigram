from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.graphql.core.caching import (
    ResponseCache,
    ResponseCacheEntry,
    _MemoryCacheShim,
    compute_cache_key,
    create_response_cache,
)


class TestMemoryCacheShim:
    @pytest.mark.asyncio
    async def test_set_and_get(self) -> None:
        cache = _MemoryCacheShim()
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_get_missing(self) -> None:
        cache = _MemoryCacheShim()
        result = await cache.get("missing")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        cache = _MemoryCacheShim()
        await cache.set("key1", "value1")
        assert await cache.delete("key1") is True
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_delete_missing(self) -> None:
        cache = _MemoryCacheShim()
        assert await cache.delete("missing") is False

    @pytest.mark.asyncio
    async def test_delete_many(self) -> None:
        cache = _MemoryCacheShim()
        await cache.set("a", 1)
        await cache.set("b", 2)
        await cache.delete_many(["a", "b"])
        assert await cache.get("a") is None
        assert await cache.get("b") is None

    @pytest.mark.asyncio
    async def test_exists(self) -> None:
        cache = _MemoryCacheShim()
        await cache.set("key1", "val")
        assert await cache.exists("key1") is True
        assert await cache.exists("missing") is False

    @pytest.mark.asyncio
    async def test_clear(self) -> None:
        cache = _MemoryCacheShim()
        await cache.set("a", 1)
        await cache.clear()
        assert await cache.get("a") is None

    @pytest.mark.asyncio
    async def test_get_many(self) -> None:
        cache = _MemoryCacheShim()
        await cache.set("a", 1)
        await cache.set("b", 2)
        result = await cache.get_many(["a", "b", "c"])
        assert result == {"a": 1, "b": 2}

    @pytest.mark.asyncio
    async def test_set_many(self) -> None:
        cache = _MemoryCacheShim()
        await cache.set_many({"a": 1, "b": 2})
        assert await cache.get("a") == 1
        assert await cache.get("b") == 2

    @pytest.mark.asyncio
    async def test_lock_acquire_release(self) -> None:
        cache = _MemoryCacheShim()
        assert await cache.acquire_lock("lock1", ttl=10) is True
        assert await cache.acquire_lock("lock1", ttl=10) is False
        assert await cache.release_lock("lock1") is True
        assert await cache.release_lock("lock1") is False


class TestComputeCacheKey:
    def test_query_only(self) -> None:
        key = compute_cache_key("query { hello }")
        assert key.startswith("gql:")
        assert len(key) == 36  # "gql:" + 32 hex chars

    def test_with_variables(self) -> None:
        key = compute_cache_key("query { hello }", variables={"id": "1"})
        assert key.startswith("gql:")

    def test_with_operation_name(self) -> None:
        key = compute_cache_key("query { hello }", operation_name="MyOp")
        assert key.startswith("gql:")

    def test_with_tenant_id(self) -> None:
        key = compute_cache_key("query { hello }", tenant_id="tenant_1")
        assert key.startswith("gql:")

    def test_with_user_id(self) -> None:
        key = compute_cache_key("query { hello }", user_id="user_1")
        assert key.startswith("gql:")

    def test_with_query_hash(self) -> None:
        key = compute_cache_key("query { hello }", query_hash="precomputed_hash_value")
        assert key.startswith("gql:precomputed_hash_value"[::1])


class TestResponseCache:
    @pytest.mark.asyncio
    async def test_get_when_disabled(self) -> None:
        backend = AsyncMock()
        cache = ResponseCache(backend=backend, enabled=False)
        result = await cache.get("key")
        assert result is None
        backend.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_when_disabled(self) -> None:
        backend = AsyncMock()
        cache = ResponseCache(backend=backend, enabled=False)
        await cache.set("key", "data")
        backend.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_and_set_enabled(self) -> None:
        backend = MagicMock()
        backend.get = AsyncMock(return_value="cached_value")
        cache = ResponseCache(backend=backend, enabled=True)
        result = await cache.get("key")
        assert result == "cached_value"

    @pytest.mark.asyncio
    async def test_set(self) -> None:
        backend = MagicMock()
        backend.set = AsyncMock()
        cache = ResponseCache(backend=backend, enabled=True)
        await cache.set("key", {"data": "hello"}, extensions={"ext": 1}, ttl=60)
        backend.set.assert_awaited_once()
        args = backend.set.call_args
        assert args[0][0] == "key"
        assert isinstance(args[0][1], ResponseCacheEntry)
        assert args[0][1].data == {"data": "hello"}

    @pytest.mark.asyncio
    async def test_invalidate(self) -> None:
        backend = MagicMock()
        backend.delete = AsyncMock()
        cache = ResponseCache(backend=backend, enabled=True)
        await cache.invalidate("key")
        backend.delete.assert_awaited_once_with("key")

    @pytest.mark.asyncio
    async def test_clear(self) -> None:
        backend = MagicMock()
        backend.clear = AsyncMock()
        cache = ResponseCache(backend=backend, enabled=True)
        await cache.clear()
        backend.clear.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_backend_error_returns_none(self) -> None:
        backend = MagicMock()
        backend.get = AsyncMock(side_effect=OSError("fail"))
        cache = ResponseCache(backend=backend, enabled=True)
        result = await cache.get("key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_backend_error_does_not_raise(self) -> None:
        backend = MagicMock()
        backend.set = AsyncMock(side_effect=RuntimeError("fail"))
        cache = ResponseCache(backend=backend, enabled=True)
        await cache.set("key", "data")
        # Should not raise

    @pytest.mark.asyncio
    async def test_invalidate_backend_error(self) -> None:
        backend = MagicMock()
        backend.delete = AsyncMock(side_effect=LookupError("fail"))
        cache = ResponseCache(backend=backend, enabled=True)
        await cache.invalidate("key")
        # Should not raise

    @pytest.mark.asyncio
    async def test_clear_backend_error(self) -> None:
        backend = MagicMock()
        backend.clear = AsyncMock(side_effect=RuntimeError("fail"))
        cache = ResponseCache(backend=backend, enabled=True)
        await cache.clear()
        # Should not raise

    def test_enabled_property(self) -> None:
        cache = ResponseCache(backend=MagicMock(), enabled=True)
        assert cache.enabled is True
        cache2 = ResponseCache(backend=MagicMock(), enabled=False)
        assert cache2.enabled is False


class TestCreateResponseCache:
    def test_memory_backend(self) -> None:
        cache = create_response_cache(backend_type="memory")
        assert isinstance(cache, ResponseCache)

    def test_unknown_backend(self) -> None:
        with pytest.raises(ValueError, match="Unknown cache backend type"):
            create_response_cache(backend_type="invalid")
