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


async def _passthrough(scope: dict, receive: object, send: object) -> None:
    """Inner app stub."""
