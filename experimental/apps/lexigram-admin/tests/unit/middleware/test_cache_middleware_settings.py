"""Tests for AdminCacheMiddleware settings store integration."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from lexigram.admin.auth.user import AdminUserRecord
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


class TestCacheKeyUserIsolation:
    """Tests for per-user cache key isolation."""

    def _scope(self, user: object | None) -> dict:
        scope = {
            "type": "http",
            "path": "/admin/dashboard",
            "method": "GET",
            "headers": [],
            "query_string": b"page=1",
        }
        if user is not None:
            scope["state"] = {"user": user}
        else:
            scope["state"] = {}
        return scope

    def _middleware(self) -> AdminCacheMiddleware:
        return AdminCacheMiddleware(app=_passthrough, cache_backend=AsyncMock())

    def test_keys_differ_between_users(self) -> None:
        mw = self._middleware()
        key_a = mw._get_cache_key(
            self._scope(AdminUserRecord(user_id="user-a", email="a@ex.com"))
        )
        key_b = mw._get_cache_key(
            self._scope(AdminUserRecord(user_id="user-b", email="b@ex.com"))
        )
        assert key_a != key_b
        assert "user-a" in key_a
        assert "user-b" in key_b

    def test_guest_key_differs_from_authenticated(self) -> None:
        mw = self._middleware()
        guest = mw._get_cache_key(self._scope(None))
        authed = mw._get_cache_key(
            self._scope(AdminUserRecord(user_id="user-a", email="a@ex.com"))
        )
        assert guest != authed
        assert ":guest" in guest
