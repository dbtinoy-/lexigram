"""Tests for AdminCacheMiddleware settings store integration."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from lexigram.admin.middleware.cache import AdminCacheMiddleware


class _SettingsStore:
    """Fake settings store with optional values."""

    def __init__(self, values: dict[str, object] | None = None) -> None:
        self.values = dict(values or {})
        self.get = AsyncMock(side_effect=self._get)

    async def _get(self, key: str, default: object | None = None) -> object | None:
        return self.values.get(key, default)


async def _passthrough(scope: dict, receive: object, send: object) -> None:
    """Inner app stub."""


class TestCacheMiddlewareSettings:
    """Tests for runtime settings overrides."""

    @pytest.mark.asyncio
    async def test_settings_disable_caching(self) -> None:
        store = _SettingsStore({"admin.cache.enabled": False})
        mw = AdminCacheMiddleware(
            app=_passthrough,
            settings_service=store,
            cache_backend=AsyncMock(),
        )
        called: list[str] = []

        async def inner(scope: dict, receive: object, send: object) -> None:
            called.append(scope.get("path", ""))

        mw.app = inner
        await mw(
            {
                "type": "http",
                "path": "/x",
                "method": "GET",
                "headers": [],
                "query_string": b"",
                "scope": {},
            },
            object(),
            object(),
        )
        assert called == ["/x"]
        assert store.get.await_count >= 1
        store.get.assert_any_await("admin.cache.enabled", True)

    @pytest.mark.asyncio
    async def test_settings_override_ttl(self) -> None:
        store = _SettingsStore(
            {"admin.cache.enabled": True, "admin.cache.default_ttl": 300}
        )
        mw = AdminCacheMiddleware(app=_passthrough, settings_service=store, ttl=60)
        assert mw.ttl == 60
        assert mw.settings_service is store
