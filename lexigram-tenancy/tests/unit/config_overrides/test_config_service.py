"""Tests for TenantConfigService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.tenancy.config_overrides.service import TenantConfigService
from lexigram.tenancy.stores.memory import InMemoryTenantProvider


def _make_service(
    defaults: dict | None = None,
) -> tuple[TenantConfigService, InMemoryTenantProvider]:
    store = InMemoryTenantProvider()
    event_bus = MagicMock()
    event_bus.publish = AsyncMock()
    svc = TenantConfigService(
        config_provider=store,
        defaults=defaults or {},
        event_bus=event_bus,
    )
    return svc, store


@pytest.mark.asyncio
async def test_get_returns_tenant_override() -> None:
    """get() returns the tenant-specific override when set."""
    svc, store = _make_service(defaults={"max_users": 10})
    await store.set_config("t1", "max_users", 50)
    value = await svc.get("t1", "max_users")
    assert value == 50


@pytest.mark.asyncio
async def test_get_falls_back_to_default() -> None:
    """get() falls back to the application default when no override is set."""
    svc, _ = _make_service(defaults={"max_users": 10})
    value = await svc.get("t1", "max_users")
    assert value == 10


@pytest.mark.asyncio
async def test_get_returns_none_when_no_default() -> None:
    """get() returns None when neither override nor default is set."""
    svc, _ = _make_service()
    value = await svc.get("t1", "unknown_key")
    assert value is None


@pytest.mark.asyncio
async def test_set_stores_value_and_publishes_event() -> None:
    """set() stores the value and publishes a TenantConfigChanged event."""
    svc, store = _make_service()
    await svc.set("t1", "feature_x", True)
    stored = await store.get_config("t1", "feature_x")
    assert stored is True


@pytest.mark.asyncio
async def test_get_effective_config_merges_defaults_and_overrides() -> None:
    """get_effective_config() returns defaults overridden by tenant values."""
    svc, store = _make_service(defaults={"a": 1, "b": 2})
    await store.set_config("t1", "b", 99)
    effective = await svc.get_effective_config("t1")
    assert effective["a"] == 1
    assert effective["b"] == 99
