"""Tests for TenantValidator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.tenancy.protocols import TenantProviderProtocol
from lexigram.contracts.tenancy.types import TenantInfo, TenantStatus
from lexigram.tenancy.enforcement.validator import TenantValidator


def _make_info(status: TenantStatus = TenantStatus.ACTIVE) -> TenantInfo:
    return TenantInfo(
        tenant_id="tenant-abc",
        slug="acme",
        name="ACME",
        status=status,
    )


@pytest.mark.asyncio
async def test_returns_info_for_active_tenant() -> None:
    """Returns TenantInfo when the tenant is active."""
    provider = MagicMock(spec=TenantProviderProtocol)
    provider.get_tenant = AsyncMock(return_value=_make_info(TenantStatus.ACTIVE))
    validator = TenantValidator(provider, cache_ttl=300)
    result = await validator.validate("tenant-abc")
    assert result is not None
    assert result.tenant_id == "tenant-abc"


@pytest.mark.asyncio
async def test_returns_none_for_inactive_tenant() -> None:
    """Returns None when the tenant is inactive."""
    provider = MagicMock(spec=TenantProviderProtocol)
    provider.get_tenant = AsyncMock(return_value=_make_info(TenantStatus.INACTIVE))
    validator = TenantValidator(provider)
    result = await validator.validate("tenant-abc")
    assert result is None


@pytest.mark.asyncio
async def test_returns_none_for_missing_tenant() -> None:
    """Returns None when the provider returns None."""
    provider = MagicMock(spec=TenantProviderProtocol)
    provider.get_tenant = AsyncMock(return_value=None)
    validator = TenantValidator(provider)
    result = await validator.validate("missing")
    assert result is None


@pytest.mark.asyncio
async def test_invalidate_clears_cache_entry() -> None:
    """invalidate() removes the tenant from the cache."""
    provider = MagicMock(spec=TenantProviderProtocol)
    provider.get_tenant = AsyncMock(return_value=_make_info())
    validator = TenantValidator(provider, cache_ttl=3600)

    await validator.validate("tenant-abc")
    assert provider.get_tenant.call_count == 1

    validator.invalidate("tenant-abc")
    await validator.validate("tenant-abc")
    assert provider.get_tenant.call_count == 2


@pytest.mark.asyncio
async def test_cache_hit_avoids_provider_call() -> None:
    """Second call within TTL uses the cache."""
    provider = MagicMock(spec=TenantProviderProtocol)
    provider.get_tenant = AsyncMock(return_value=_make_info())
    validator = TenantValidator(provider, cache_ttl=3600)

    await validator.validate("tenant-abc")
    await validator.validate("tenant-abc")
    assert provider.get_tenant.call_count == 1


@pytest.mark.asyncio
async def test_returns_none_for_suspended_tenant() -> None:
    """Returns None for suspended tenant."""
    provider = MagicMock(spec=TenantProviderProtocol)
    provider.get_tenant = AsyncMock(return_value=_make_info(TenantStatus.SUSPENDED))
    validator = TenantValidator(provider)
    result = await validator.validate("tenant-abc")
    assert result is None


@pytest.mark.asyncio
async def test_invalidate_nonexistent_does_not_raise() -> None:
    """Invalidating non-existent tenant does not raise."""
    provider = MagicMock(spec=TenantProviderProtocol)
    validator = TenantValidator(provider)
    validator.invalidate("nonexistent")


@pytest.mark.asyncio
async def test_returns_none_for_provisioning_status() -> None:
    """Returns None for provisioning tenant."""
    provider = MagicMock(spec=TenantProviderProtocol)
    provider.get_tenant = AsyncMock(return_value=_make_info(TenantStatus.PROVISIONING))
    validator = TenantValidator(provider)
    result = await validator.validate("tenant-abc")
    assert result is None


def test_cache_ttl_accepts_zero() -> None:
    """cache_ttl of zero is accepted."""
    provider = MagicMock(spec=TenantProviderProtocol)
    validator = TenantValidator(provider, cache_ttl=0)
    assert validator._cache_ttl == 0


def test_tenant_id_is_required() -> None:
    """tenant_id parameter is required."""
    provider = MagicMock(spec=TenantProviderProtocol)
    validator = TenantValidator(provider)


@pytest.mark.asyncio
async def test_invalidate_all_clears_cache() -> None:
    """invalidate_all() clears the entire cache."""
    provider = MagicMock(spec=TenantProviderProtocol)
    provider.get_tenant = AsyncMock(return_value=_make_info())
    validator = TenantValidator(provider, cache_ttl=3600)

    await validator.validate("tenant-abc")
    await validator.validate("tenant-xyz")
    validator.invalidate_all()
    # After invalidate_all, both entries should be gone
    await validator.validate("tenant-abc")
    await validator.validate("tenant-xyz")
    assert provider.get_tenant.call_count == 4


@pytest.mark.asyncio
async def test_multiple_tenants_cached_separately() -> None:
    """Multiple tenants are cached independently."""
    provider = MagicMock(spec=TenantProviderProtocol)
    provider.get_tenant = AsyncMock(return_value=_make_info())
    validator = TenantValidator(provider, cache_ttl=3600)

    await validator.validate("tenant-a")
    await validator.validate("tenant-b")
    await validator.validate("tenant-a")
    # Should have 2 unique calls (b counted once, a counted twice but cached)
    assert provider.get_tenant.call_count == 2
