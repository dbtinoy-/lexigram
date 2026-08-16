"""Tests for CachedTenantConfigProvider."""

from __future__ import annotations

import pytest

from lexigram.tenancy.config_overrides.cache import CachedTenantConfigProvider
from lexigram.tenancy.stores.memory import InMemoryTenantProvider


@pytest.mark.asyncio
async def test_get_config_returns_value() -> None:
    """get_config() returns a stored value."""
    store = InMemoryTenantProvider()
    await store.set_config("t1", "key", "value")
    cached = CachedTenantConfigProvider(inner=store, ttl=60)
    result = await cached.get_config("t1", "key")
    assert result == "value"


@pytest.mark.asyncio
async def test_cache_hit_avoids_backend_call() -> None:
    """Second get_all_config within TTL uses the in-memory cache."""
    from unittest.mock import AsyncMock, patch

    store = InMemoryTenantProvider()
    await store.set_config("t1", "x", 1)
    cached = CachedTenantConfigProvider(inner=store, ttl=3600)

    # Warm the cache
    await cached.get_all_config("t1")
    # Patch inner to verify it's not called again
    store.get_all_config = AsyncMock(return_value={"x": 1})
    await cached.get_all_config("t1")
    store.get_all_config.assert_not_called()


@pytest.mark.asyncio
async def test_set_config_invalidates_cache() -> None:
    """set_config() clears the cached dict so the next get fetches fresh data."""
    store = InMemoryTenantProvider()
    cached = CachedTenantConfigProvider(inner=store, ttl=3600)

    await store.set_config("t1", "y", 10)
    await cached.get_all_config("t1")  # warm cache

    # Now update and immediately read — should reflect new value
    await cached.set_config("t1", "y", 20)
    result = await cached.get_config("t1", "y")
    assert result == 20


@pytest.mark.asyncio
async def test_get_config_returns_none_for_missing_key() -> None:
    """get_config() returns None when key is not set."""
    store = InMemoryTenantProvider()
    cached = CachedTenantConfigProvider(inner=store, ttl=60)
    result = await cached.get_config("t1", "nonexistent")
    assert result is None
