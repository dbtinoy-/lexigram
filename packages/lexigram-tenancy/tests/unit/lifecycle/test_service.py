"""Tests for TenantLifecycleService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.tenancy.commands import CreateTenantCommand, UpdateTenantCommand
from lexigram.contracts.tenancy.errors import TenantNotFoundError, TenantSlugConflictError
from lexigram.contracts.tenancy.protocols import TenantProviderProtocol
from lexigram.result import Err, Ok
from lexigram.tenancy.enforcement.validator import TenantValidator
from lexigram.tenancy.lifecycle.provisioner import TenantProvisioner
from lexigram.tenancy.lifecycle.service import TenantLifecycleService
from lexigram.tenancy.stores.memory import InMemoryTenantProvider


def _make_service(
    provider: TenantProviderProtocol | None = None,
    auto_provision: bool = False,
) -> tuple[TenantLifecycleService, InMemoryTenantProvider]:
    from lexigram.tenancy.isolation.row_level import RowLevelIsolationStrategy

    store = InMemoryTenantProvider() if provider is None else provider
    strategy = RowLevelIsolationStrategy()
    provisioner = TenantProvisioner(strategy=strategy, auto_provision=auto_provision)
    validator = TenantValidator(store, cache_ttl=300)
    event_bus = MagicMock()
    event_bus.publish = AsyncMock()
    svc = TenantLifecycleService(
        provider=store,
        provisioner=provisioner,
        event_bus=event_bus,
        validator=validator,
    )
    return svc, store


@pytest.mark.asyncio
async def test_create_tenant_succeeds() -> None:
    """Creating a new tenant returns Ok(TenantInfo)."""
    svc, _ = _make_service()
    cmd = CreateTenantCommand(slug="acme", name="ACME Corp")
    result = await svc.create_tenant(cmd)
    assert result.is_ok()
    tenant = result.unwrap()
    assert tenant.slug == "acme"
    assert tenant.name == "ACME Corp"


@pytest.mark.asyncio
async def test_create_tenant_slug_conflict() -> None:
    """Creating a tenant with a duplicate slug returns Err(TenantSlugConflictError)."""
    svc, _ = _make_service()
    cmd = CreateTenantCommand(slug="acme", name="ACME 1")
    await svc.create_tenant(cmd)

    result2 = await svc.create_tenant(CreateTenantCommand(slug="acme", name="ACME 2"))
    assert result2.is_err()
    assert isinstance(result2.unwrap_err(), TenantSlugConflictError)


@pytest.mark.asyncio
async def test_deactivate_tenant_succeeds() -> None:
    """Deactivating a tenant returns Ok(None) and publishes an event."""
    svc, store = _make_service()
    create_result = await svc.create_tenant(CreateTenantCommand(slug="beta", name="Beta"))
    tenant = create_result.unwrap()

    result = await svc.deactivate_tenant(tenant.tenant_id)
    assert result.is_ok()


@pytest.mark.asyncio
async def test_deactivate_missing_tenant_returns_err() -> None:
    """Deactivating a non-existent tenant returns Err."""
    svc, _ = _make_service()
    result = await svc.deactivate_tenant("no-such-tenant")
    assert result.is_err()
    assert isinstance(result.unwrap_err(), TenantNotFoundError)


@pytest.mark.asyncio
async def test_activate_tenant() -> None:
    """Activating a deactivated tenant returns Ok(None)."""
    svc, store = _make_service()
    create_result = await svc.create_tenant(CreateTenantCommand(slug="gamma", name="Gamma"))
    tenant = create_result.unwrap()
    await svc.deactivate_tenant(tenant.tenant_id)

    result = await svc.activate_tenant(tenant.tenant_id)
    assert result.is_ok()
