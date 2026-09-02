"""Tests for SecurityHeadersMiddleware settings store integration."""

from __future__ import annotations

import time
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
    async def test_resolution_is_cached_within_ttl(self) -> None:
        store = _SettingsStore({"admin.security.hsts_max_age": 3600})
        mw = SecurityHeadersMiddleware(app=_passthrough, settings_store=store)
        first = await mw._resolve_headers()
        second = await mw._resolve_headers()
        assert first is second
        # csp + hsts + frame_options + csp_report_only — one read each,
        # resolved once per TTL window.
        assert store.get.await_count == 4


class TestSecurityHeadersTtl:
    """R37: settings changes take effect within one TTL window."""

    @pytest.mark.asyncio
    async def test_ttl_expiry_rereads_and_picks_up_changes(self) -> None:
        store = _SettingsStore({"admin.security.frame_options": "DENY"})
        mw = SecurityHeadersMiddleware(
            app=_passthrough, settings_store=store, settings_ttl=30.0
        )
        first = await mw._resolve_headers()
        assert first._headers["X-Frame-Options"] == "DENY"

        # Simulate a panel save + TTL lapse.
        store.values["admin.security.frame_options"] = "SAMEORIGIN"
        mw._resolved_at = time.monotonic() - 31.0
        second = await mw._resolve_headers()
        assert second is not first
        assert second._headers["X-Frame-Options"] == "SAMEORIGIN"
        assert store.get.await_count == 8

    @pytest.mark.asyncio
    async def test_report_only_kill_switch_applies_without_restart(self) -> None:
        store = _SettingsStore({})
        mw = SecurityHeadersMiddleware(
            app=_passthrough, settings_store=store, settings_ttl=30.0
        )
        first = await mw._resolve_headers()
        assert "Content-Security-Policy-Report-Only" in first._headers

        store.values["admin.security.csp_report_only"] = "off"
        mw._resolved_at = time.monotonic() - 31.0
        second = await mw._resolve_headers()
        assert "Content-Security-Policy-Report-Only" not in second._headers

    @pytest.mark.asyncio
    async def test_refresh_error_keeps_last_good_service(self) -> None:
        store = _SettingsStore({"admin.security.frame_options": "SAMEORIGIN"})
        mw = SecurityHeadersMiddleware(
            app=_passthrough, settings_store=store, settings_ttl=30.0
        )
        first = await mw._resolve_headers()
        assert first._headers["X-Frame-Options"] == "SAMEORIGIN"

        store.get = AsyncMock(side_effect=RuntimeError("db down"))
        mw._resolved_at = time.monotonic() - 31.0
        second = await mw._resolve_headers()
        # Stale-but-consistent: no silent downgrade to compile-time defaults.
        assert second is first
        assert second._headers["X-Frame-Options"] == "SAMEORIGIN"
        # The retry timestamp advanced — the flapping store is not hammered
        # again on the immediately following request.
        third = await mw._resolve_headers()
        assert third is first
        assert store.get.await_count == 1

    @pytest.mark.asyncio
    async def test_invalidate_forces_immediate_reread(self) -> None:
        store = _SettingsStore({"admin.security.frame_options": "DENY"})
        mw = SecurityHeadersMiddleware(
            app=_passthrough, settings_store=store, settings_ttl=30.0
        )
        await mw._resolve_headers()
        store.values["admin.security.frame_options"] = "SAMEORIGIN"
        mw.invalidate()
        refreshed = await mw._resolve_headers()
        assert refreshed._headers["X-Frame-Options"] == "SAMEORIGIN"

    @pytest.mark.asyncio
    async def test_zero_ttl_caches_forever(self) -> None:
        store = _SettingsStore({"admin.security.frame_options": "DENY"})
        mw = SecurityHeadersMiddleware(
            app=_passthrough, settings_store=store, settings_ttl=0
        )
        first = await mw._resolve_headers()
        # Even a lapsed timestamp must not trigger a re-read.
        mw._resolved_at = time.monotonic() - 3600.0
        second = await mw._resolve_headers()
        assert second is first
        assert store.get.await_count == 4


async def _passthrough(scope: dict, receive: object, send: object) -> None:
    """Inner app stub."""
