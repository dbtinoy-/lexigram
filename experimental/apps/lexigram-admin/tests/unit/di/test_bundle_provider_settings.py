"""Tests for settings DI wiring helpers."""

from __future__ import annotations

import pytest

from lexigram.admin.settings.panel.registry import ConfigRegistry
from lexigram.admin.settings.store import DEFAULT_TENANT, TenantConfigStore


class _FakeService:
    def __init__(self) -> None:
        self._data: dict[tuple[str, str], object] = {}

    async def get(self, tenant: str, name: str) -> object | None:
        return self._data.get((tenant, name))

    async def set(self, tenant: str, name: str, value: object) -> None:
        self._data[(tenant, name)] = value


class TestStoreRegistrationHelper:
    """Tests for the helper used by bundle_provider to attach the db store."""

    @pytest.mark.asyncio
    async def test_build_store_round_trip(self) -> None:
        registry = ConfigRegistry.with_defaults()
        svc = _FakeService()
        store = TenantConfigStore(svc, tenant_id=DEFAULT_TENANT)
        registry.register_store("db", store)

        assert registry.has_store("db")
        await registry.save_values(
            "admin.cache", {"enabled": "false", "default_ttl": "90"}, store_name="db"
        )
        values = await registry.get_values("admin.cache", store_name="db")
        assert values["enabled"] is False
        assert values["default_ttl"] == 90

    @pytest.mark.asyncio
    async def test_register_db_store_idempotent(self) -> None:
        registry = ConfigRegistry.with_defaults()
        svc = _FakeService()
        registry.register_store("db", TenantConfigStore(svc))
        registry.register_store("db", TenantConfigStore(svc))
        assert registry.has_store("db")
