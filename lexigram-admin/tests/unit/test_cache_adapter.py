"""Tests for cache adapter delegating to lexigram-cache."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.cache.adapter import AdminCacheServiceAdapter


class _FakeCacheService:
    """Minimal fake matching CacheService protocol."""

    def __init__(self) -> None:
        self._data: dict[str, object] = {}

    async def get(self, key: str) -> object | None:
        return self._data.get(key)

    async def set(self, key: str, value: object, ttl: int | None = None) -> None:
        self._data[key] = value

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)

    async def delete_pattern(self, pattern: str) -> int:
        before = len(self._data)
        self._data = {k: v for k, v in self._data.items() if pattern not in k}
        return before - len(self._data)

    async def get_or_set(
        self,
        key: str,
        factory: object,
        ttl: int | None = None,
    ) -> object:
        if key in self._data:
            return self._data[key]
        value = await factory() if callable(factory) else factory
        self._data[key] = value
        return value

    async def exists(self, key: str) -> bool:
        return key in self._data

    async def clear(self) -> None:
        self._data.clear()


class TestAdminCacheServiceAdapter:
    @pytest.mark.asyncio
    async def test_get_returns_value(self) -> None:
        svc = _FakeCacheService()
        await svc.set("key", "value")
        adapter = AdminCacheServiceAdapter(cache_service=svc)
        assert await adapter.get("key") == "value"

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing(self) -> None:
        adapter = AdminCacheServiceAdapter(cache_service=_FakeCacheService())
        assert await adapter.get("missing") is None

    @pytest.mark.asyncio
    async def test_set_stores_value(self) -> None:
        svc = _FakeCacheService()
        adapter = AdminCacheServiceAdapter(cache_service=svc)
        result = await adapter.set("k", "v", ttl=60)
        assert result is True
        assert await svc.get("k") == "v"

    @pytest.mark.asyncio
    async def test_delete_removes_value(self) -> None:
        svc = _FakeCacheService()
        await svc.set("k", "v")
        adapter = AdminCacheServiceAdapter(cache_service=svc)
        result = await adapter.delete("k")
        assert result is True
        assert await svc.get("k") is None

    @pytest.mark.asyncio
    async def test_delete_pattern_matches(self) -> None:
        svc = _FakeCacheService()
        await svc.set("foo:1", "a")
        await svc.set("foo:2", "b")
        await svc.set("bar:1", "c")
        adapter = AdminCacheServiceAdapter(cache_service=svc)
        count = await adapter.delete_pattern("foo:")
        assert count == 2
        assert await svc.get("foo:1") is None
        assert await svc.get("bar:1") == "c"

    @pytest.mark.asyncio
    async def test_get_or_set_computes(self) -> None:
        svc = _FakeCacheService()
        adapter = AdminCacheServiceAdapter(cache_service=svc)

        async def factory() -> str:
            return "computed"

        result = await adapter.get_or_set("k", factory)
        assert result == "computed"
        assert await svc.get("k") == "computed"

    @pytest.mark.asyncio
    async def test_get_or_set_uses_cached(self) -> None:
        svc = _FakeCacheService()
        await svc.set("k", "cached")
        adapter = AdminCacheServiceAdapter(cache_service=svc)

        async def factory() -> str:
            return "computed"

        result = await adapter.get_or_set("k", factory)
        assert result == "cached"

    @pytest.mark.asyncio
    async def test_exists_returns_true(self) -> None:
        svc = _FakeCacheService()
        await svc.set("k", "v")
        adapter = AdminCacheServiceAdapter(cache_service=svc)
        assert await adapter.exists("k") is True

    @pytest.mark.asyncio
    async def test_exists_returns_false(self) -> None:
        adapter = AdminCacheServiceAdapter(cache_service=_FakeCacheService())
        assert await adapter.exists("nope") is False

    @pytest.mark.asyncio
    async def test_clear_empties_cache(self) -> None:
        svc = _FakeCacheService()
        await svc.set("a", 1)
        await svc.set("b", 2)
        adapter = AdminCacheServiceAdapter(cache_service=svc)
        result = await adapter.clear()
        assert result is True
        assert await svc.get("a") is None
        assert await svc.get("b") is None

    # -- null / no-op mode (cache_service = None) -- #

    @pytest.mark.asyncio
    async def test_null_get_returns_none(self) -> None:
        adapter = AdminCacheServiceAdapter(cache_service=None)
        assert await adapter.get("anything") is None

    @pytest.mark.asyncio
    async def test_null_set_returns_false(self) -> None:
        adapter = AdminCacheServiceAdapter(cache_service=None)
        assert await adapter.set("k", "v") is False

    @pytest.mark.asyncio
    async def test_null_delete_returns_false(self) -> None:
        adapter = AdminCacheServiceAdapter(cache_service=None)
        assert await adapter.delete("k") is False

    @pytest.mark.asyncio
    async def test_null_delete_pattern_returns_zero(self) -> None:
        adapter = AdminCacheServiceAdapter(cache_service=None)
        assert await adapter.delete_pattern("foo:") == 0

    @pytest.mark.asyncio
    async def test_null_get_or_set_calls_factory(self) -> None:
        adapter = AdminCacheServiceAdapter(cache_service=None)

        async def factory() -> str:
            return "computed"

        result = await adapter.get_or_set("k", factory)
        assert result == "computed"

    @pytest.mark.asyncio
    async def test_null_exists_returns_false(self) -> None:
        adapter = AdminCacheServiceAdapter(cache_service=None)
        assert await adapter.exists("anything") is False

    @pytest.mark.asyncio
    async def test_null_clear_returns_false(self) -> None:
        adapter = AdminCacheServiceAdapter(cache_service=None)
        assert await adapter.clear() is False
