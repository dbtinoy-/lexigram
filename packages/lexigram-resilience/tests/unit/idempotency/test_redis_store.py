"""Unit tests for RedisIdempotencyStore.

Tests the store against a mock ``CacheBackendProtocol``, verifying that:
- ``get`` / ``set`` / ``delete`` correctly delegate to the cache backend.
- TTL ``float`` is rounded up to the nearest ``int`` for the backend.
- The configured key prefix is prepended to every cache key.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.exceptions.idempotency import IdempotencyStoreError
from lexigram.contracts.infra.cache.exceptions import CacheError
from lexigram.resilience.idempotency.redis import RedisIdempotencyStore
from lexigram.result import Err, Ok


@pytest.fixture
def mock_cache() -> MagicMock:
    """Return a mock ``CacheBackendProtocol``."""
    cache = MagicMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    cache.delete = AsyncMock(return_value=True)
    return cache


@pytest.fixture
def store(mock_cache: MagicMock) -> RedisIdempotencyStore:
    """Return a ``RedisIdempotencyStore`` wired to the mock cache."""
    return RedisIdempotencyStore(cache=mock_cache, key_prefix="test:")


class TestRedisIdempotencyStoreGet:
    @pytest.mark.asyncio
    async def test_get_delegates_to_cache(
        self, store: RedisIdempotencyStore, mock_cache: MagicMock
    ) -> None:
        """get() calls cache.get with the prefixed key."""
        mock_cache.get = AsyncMock(return_value={"result": 42})

        value = await store.get("req-123")

        mock_cache.get.assert_awaited_once_with("test:req-123")
        assert value == {"result": 42}

    @pytest.mark.asyncio
    async def test_get_returns_none_when_cache_miss(
        self, store: RedisIdempotencyStore, mock_cache: MagicMock
    ) -> None:
        """get() returns None when the key is absent."""
        mock_cache.get = AsyncMock(return_value=None)

        value = await store.get("missing-key")

        assert value is None

    @pytest.mark.asyncio
    async def test_get_unwraps_ok_result(
        self, store: RedisIdempotencyStore, mock_cache: MagicMock
    ) -> None:
        """get() unwraps an Ok result returned by the cache backend."""
        mock_cache.get = AsyncMock(return_value=Ok("stored-result"))

        value = await store.get("req-ok")

        assert value == "stored-result"

    @pytest.mark.asyncio
    async def test_get_returns_none_for_ok_none(
        self, store: RedisIdempotencyStore, mock_cache: MagicMock
    ) -> None:
        """get() returns None when the backend reports a miss as Ok(None)."""
        mock_cache.get = AsyncMock(return_value=Ok(None))

        value = await store.get("req-miss")

        assert value is None

    @pytest.mark.asyncio
    async def test_get_raises_idempotency_store_error_on_cache_err(
        self, store: RedisIdempotencyStore, mock_cache: MagicMock
    ) -> None:
        """get() raises IdempotencyStoreError when the backend returns Err.

        The raise is chained from the underlying cache error so operators can
        see the root cause — never a bare UnwrapError.
        """
        cache_error = CacheError("backend down")
        mock_cache.get = AsyncMock(return_value=Err(cache_error))

        with pytest.raises(IdempotencyStoreError) as excinfo:
            await store.get("req-err")

        assert excinfo.value.__cause__ is cache_error
        assert "req-err" in str(excinfo.value)


class TestRedisIdempotencyStoreSet:
    @pytest.mark.asyncio
    async def test_set_delegates_to_cache_with_prefix(
        self, store: RedisIdempotencyStore, mock_cache: MagicMock
    ) -> None:
        """set() calls cache.set with the prefixed key and no TTL."""
        await store.set("req-abc", {"status": "ok"})

        mock_cache.set.assert_awaited_once_with(
            "test:req-abc", {"status": "ok"}, ttl=None
        )

    @pytest.mark.asyncio
    async def test_set_converts_float_ttl_to_int(
        self, store: RedisIdempotencyStore, mock_cache: MagicMock
    ) -> None:
        """set() rounds a float TTL up to the nearest int for the cache backend."""
        await store.set("req-ttl", "value", ttl=1.1)

        mock_cache.set.assert_awaited_once_with("test:req-ttl", "value", ttl=2)

    @pytest.mark.asyncio
    async def test_set_rounds_exact_int_ttl(
        self, store: RedisIdempotencyStore, mock_cache: MagicMock
    ) -> None:
        """set() passes integer TTL without modification when value is exact."""
        await store.set("req-ttl", "value", ttl=5.0)

        mock_cache.set.assert_awaited_once_with("test:req-ttl", "value", ttl=5)


class TestRedisIdempotencyStoreDelete:
    @pytest.mark.asyncio
    async def test_delete_delegates_to_cache_with_prefix(
        self, store: RedisIdempotencyStore, mock_cache: MagicMock
    ) -> None:
        """delete() calls cache.delete with the prefixed key."""
        await store.delete("req-del")

        mock_cache.delete.assert_awaited_once_with("test:req-del")


class TestRedisIdempotencyStorePrefix:
    @pytest.mark.asyncio
    async def test_default_prefix_is_applied(self, mock_cache: MagicMock) -> None:
        """Store uses 'idempotency:' as the default key prefix."""
        default_store = RedisIdempotencyStore(cache=mock_cache)
        await default_store.get("some-key")

        mock_cache.get.assert_awaited_once_with("idempotency:some-key")

    @pytest.mark.asyncio
    async def test_custom_prefix_is_applied(self, mock_cache: MagicMock) -> None:
        """Store applies the configured custom key prefix."""
        custom_store = RedisIdempotencyStore(cache=mock_cache, key_prefix="app:")
        await custom_store.set("key", "v")

        mock_cache.set.assert_awaited_once_with("app:key", "v", ttl=None)
