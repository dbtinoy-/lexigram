"""Tests for TenantConfigStore."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from lexigram.admin.settings.store import TenantConfigStore


class _FakeSettingsService:
    """Minimal stand-in for AdminSettingsService."""

    def __init__(self, values: dict[str, object] | None = None) -> None:
        self.values = dict(values or {})
        self.get = AsyncMock(side_effect=self._get)
        self.set = AsyncMock(side_effect=self._set)

    async def _get(self, tenant: str, name: str) -> object | None:
        return self.values.get(name)

    async def _set(self, tenant: str, name: str, value: object) -> None:
        self.values[name] = value


class TestTenantConfigStore:
    """Tests for the ConfigRegistry StoreBase adapter."""

    @pytest.mark.asyncio
    async def test_get_returns_stored_value(self) -> None:
        svc = _FakeSettingsService({"admin.cache.enabled": True})
        store = TenantConfigStore(svc, tenant_id="acme")
        assert await store.get("admin.cache.enabled", default=None) is True
        svc.get.assert_awaited_once_with("acme", "admin.cache.enabled")

    @pytest.mark.asyncio
    async def test_get_returns_default_when_missing(self) -> None:
        store = TenantConfigStore(_FakeSettingsService())
        assert await store.get("admin.cache.enabled", default=True) is True

    @pytest.mark.asyncio
    async def test_set_persists_value(self) -> None:
        svc = _FakeSettingsService()
        store = TenantConfigStore(svc)
        await store.set("admin.cache.default_ttl", 120)
        assert svc.values["admin.cache.default_ttl"] == 120

    @pytest.mark.asyncio
    async def test_default_tenant_is_default(self) -> None:
        svc = _FakeSettingsService({"admin.cache.enabled": True})
        store = TenantConfigStore(svc)
        await store.get("admin.cache.enabled")
        svc.get.assert_awaited_once_with("default", "admin.cache.enabled")


class TestTenantConfigStoreOverride:
    """Per-call tenant_id takes precedence over the constructor default."""

    @pytest.mark.asyncio
    async def test_explicit_tenant_id_overrides_constructor_default(self) -> None:
        svc = _FakeSettingsService()
        store = TenantConfigStore(svc, tenant_id="tenant-a")

        await store.get("k", tenant_id="tenant-b")
        svc.get.assert_awaited_once_with("tenant-b", "k")

    @pytest.mark.asyncio
    async def test_no_tenant_id_falls_back_to_constructor_default(self) -> None:
        svc = _FakeSettingsService()
        store = TenantConfigStore(svc, tenant_id="tenant-a")

        await store.get("k")
        svc.get.assert_awaited_once_with("tenant-a", "k")
