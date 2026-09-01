"""Tests for SecurityHeadersMiddleware settings store integration."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from lexigram.admin.middleware.security_headers import (
    AdminSecurityHeaders,
    SecurityHeadersMiddleware,
)


class _SettingsStore:
    """Fake settings store."""

    def __init__(self, values: dict[str, object] | None = None) -> None:
        self.values = dict(values or {})
        self.get = AsyncMock(side_effect=self._get)

    async def _get(self, key: str, default: object | None = None) -> object | None:
        return self.values.get(key, default)


class TestSecurityHeadersSettings:
    """Tests for runtime CSP/HSTS overrides."""

    @pytest.mark.asyncio
    async def test_uses_default_csp_when_store_empty(self) -> None:
        mw = SecurityHeadersMiddleware(
            app=_passthrough, settings_store=_SettingsStore()
        )
        service = await mw._resolve_headers()
        assert isinstance(service, AdminSecurityHeaders)

    @pytest.mark.asyncio
    async def test_csp_override_from_store(self) -> None:
        store = _SettingsStore(
            {"admin.security.csp": "default-src 'self'; script-src 'none'"}
        )
        mw = SecurityHeadersMiddleware(app=_passthrough, settings_store=store)
        service = await mw._resolve_headers()
        assert service._headers["Content-Security-Policy"] == (
            "default-src 'self'; script-src 'none'"
        )

    @pytest.mark.asyncio
    async def test_hsts_override_from_store(self) -> None:
        store = _SettingsStore({"admin.security.hsts_max_age": 3600})
        mw = SecurityHeadersMiddleware(app=_passthrough, settings_store=store)
        service = await mw._resolve_headers()
        assert "max-age=3600" in service._headers["Strict-Transport-Security"]

    @pytest.mark.asyncio
    async def test_frame_options_override_from_store(self) -> None:
        store = _SettingsStore({"admin.security.frame_options": "SAMEORIGIN"})
        mw = SecurityHeadersMiddleware(app=_passthrough, settings_store=store)
        service = await mw._resolve_headers()
        assert service._headers["X-Frame-Options"] == "SAMEORIGIN"

    @pytest.mark.asyncio
    async def test_empty_frame_options_omits_header(self) -> None:
        store = _SettingsStore({"admin.security.frame_options": ""})
        mw = SecurityHeadersMiddleware(app=_passthrough, settings_store=store)
        service = await mw._resolve_headers()
        assert "X-Frame-Options" not in service._headers
        # Other defaults are untouched by the frame override.
        assert "Content-Security-Policy" in service._headers

    @pytest.mark.asyncio
    async def test_unset_frame_options_defaults_to_deny(self) -> None:
        store = _SettingsStore({"admin.security.hsts_max_age": 3600})
        mw = SecurityHeadersMiddleware(app=_passthrough, settings_store=store)
        service = await mw._resolve_headers()
        assert service._headers["X-Frame-Options"] == "DENY"

    @pytest.mark.asyncio
    async def test_store_error_falls_back_to_defaults(self) -> None:
        store = _SettingsStore()
        store.get = AsyncMock(side_effect=RuntimeError("db down"))
        mw = SecurityHeadersMiddleware(app=_passthrough, settings_store=store)
        service = await mw._resolve_headers()
        assert service._headers["X-Frame-Options"] == "DENY"

    @pytest.mark.asyncio
    async def test_resolution_is_cached_once_per_process(self) -> None:
        store = _SettingsStore({"admin.security.hsts_max_age": 3600})
        mw = SecurityHeadersMiddleware(app=_passthrough, settings_store=store)
        first = await mw._resolve_headers()
        second = await mw._resolve_headers()
        assert first is second
        assert store.get.await_count == 3


async def _passthrough(scope: dict, receive: object, send: object) -> None:
    """Inner app stub."""
