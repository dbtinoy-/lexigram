"""Tests for InMemoryTenantProvider."""

from __future__ import annotations

from datetime import datetime

import pytest

from lexigram.contracts.tenancy.commands import CreateTenantCommand, UpdateTenantCommand
from lexigram.contracts.tenancy.errors import TenantNotFoundError
from lexigram.contracts.tenancy.types import TenantInfo, TenantStatus
from lexigram.result import Err, Ok
from lexigram.tenancy.stores.memory import InMemoryTenantProvider


@pytest.mark.asyncio
async def test_get_tenant_returns_none_when_not_found() -> None:
    """Returns None for non-existent tenant."""
    provider = InMemoryTenantProvider()
    result = await provider.get_tenant("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_get_tenant_returns_tenant_when_exists() -> None:
    """Returns tenant info when exists."""
    provider = InMemoryTenantProvider()
    await provider.create_tenant(
        CreateTenantCommand(slug="test-slug", name="Test Tenant")
    )
    result = await provider.get_tenant("test-slug")
    # create_tenant generates a UUID
    result = await provider.get_tenant(result.tenant_id)
    assert result is not None


@pytest.mark.asyncio
async def test_get_tenant_by_slug_returns_none_when_not_found() -> None:
    """Returns None when slug not found."""
    provider = InMemoryTenantProvider()
    result = await provider.get_tenant_by_slug("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_list_tenants_returns_empty_when_empty() -> None:
    """Returns empty list when no tenants."""
    provider = InMemoryTenantProvider()
    result = await provider.list_tenants()
    assert result == []


@pytest.mark.asyncio
async def test_get_tenant_returns_tenant_when_exists() -> None:
    """Returns tenant info when exists."""
    provider = InMemoryTenantProvider()
    create_result = await provider.create_tenant(
        CreateTenantCommand(slug="test-slug", name="Test Tenant")
    )
    tenant_id = create_result.unwrap().tenant_id
    result = await provider.get_tenant(tenant_id)
    assert result is not None
    assert result.slug == "test-slug"


@pytest.mark.asyncio
async def test_list_tenants_returns_all_when_active_only_false() -> None:
    """Returns inactive tenants when active_only=False."""
    provider = InMemoryTenantProvider()
    create_result = await provider.create_tenant(
        CreateTenantCommand(slug="test", name="Test")
    )
    tenant_id = create_result.unwrap().tenant_id
    await provider.deactivate_tenant(tenant_id)
    result = await provider.list_tenants(active_only=False)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_create_tenant_returns_ok_with_info() -> None:
    """Returns Ok with TenantInfo on create."""
    provider = InMemoryTenantProvider()
    result = await provider.create_tenant(
        CreateTenantCommand(slug="new-slug", name="New Tenant")
    )
    assert result.is_ok()
    assert result.unwrap().slug == "new-slug"


@pytest.mark.asyncio
async def test_create_tenant_generates_uuid() -> None:
    """Generates unique tenant_id."""
    provider = InMemoryTenantProvider()
    result1 = await provider.create_tenant(
        CreateTenantCommand(slug="slug1", name="Tenant 1")
    )
    result2 = await provider.create_tenant(
        CreateTenantCommand(slug="slug2", name="Tenant 2")
    )
    assert result1.unwrap().tenant_id != result2.unwrap().tenant_id


@pytest.mark.asyncio
async def test_update_tenant_returns_err_when_not_found() -> None:
    """Returns Err when tenant not found."""
    provider = InMemoryTenantProvider()
    result = await provider.update_tenant(
        "nonexistent", UpdateTenantCommand(name="New Name")
    )
    assert result.is_err()


@pytest.mark.asyncio
async def test_update_tenant_returns_ok_with_updated() -> None:
    """Returns Ok with updated info."""
    provider = InMemoryTenantProvider()
    create_result = await provider.create_tenant(
        CreateTenantCommand(slug="test", name="Original")
    )
    tenant_id = create_result.unwrap().tenant_id
    result = await provider.update_tenant(
        tenant_id, UpdateTenantCommand(name="Updated")
    )
    assert result.is_ok()
    assert result.unwrap().name == "Updated"


@pytest.mark.asyncio
async def test_deactivate_tenant_returns_err_when_not_found() -> None:
    """Returns Err when tenant not found."""
    provider = InMemoryTenantProvider()
    result = await provider.deactivate_tenant("nonexistent")
    assert result.is_err()


@pytest.mark.asyncio
async def test_deactivate_tenant_sets_status_inactive() -> None:
    """Sets status to INACTIVE."""
    provider = InMemoryTenantProvider()
    create_result = await provider.create_tenant(
        CreateTenantCommand(slug="test", name="Test")
    )
    tenant_id = create_result.unwrap().tenant_id
    await provider.deactivate_tenant(tenant_id)
    tenant = await provider.get_tenant(tenant_id)
    assert tenant is not None
    assert tenant.status == TenantStatus.INACTIVE


@pytest.mark.asyncio
async def test_activate_tenant_returns_err_when_not_found() -> None:
    """Returns Err when tenant not found."""
    provider = InMemoryTenantProvider()
    result = await provider.activate_tenant("nonexistent")
    assert result.is_err()


@pytest.mark.asyncio
async def test_activate_tenant_sets_status_active() -> None:
    """Sets status to ACTIVE."""
    provider = InMemoryTenantProvider()
    create_result = await provider.create_tenant(
        CreateTenantCommand(slug="test", name="Test")
    )
    tenant_id = create_result.unwrap().tenant_id
    await provider.deactivate_tenant(tenant_id)
    await provider.activate_tenant(tenant_id)
    tenant = await provider.get_tenant(tenant_id)
    assert tenant is not None
    assert tenant.status == TenantStatus.ACTIVE


@pytest.mark.asyncio
async def test_suspend_tenant_returns_err_when_not_found() -> None:
    """Returns Err when tenant not found."""
    provider = InMemoryTenantProvider()
    result = await provider.suspend_tenant("nonexistent")
    assert result.is_err()


@pytest.mark.asyncio
async def test_suspend_tenant_sets_status_suspended() -> None:
    """Sets status to SUSPENDED."""
    provider = InMemoryTenantProvider()
    create_result = await provider.create_tenant(
        CreateTenantCommand(slug="test", name="Test")
    )
    tenant_id = create_result.unwrap().tenant_id
    await provider.suspend_tenant(tenant_id, "test reason")
    tenant = await provider.get_tenant(tenant_id)
    assert tenant is not None
    assert tenant.status == TenantStatus.SUSPENDED


@pytest.mark.asyncio
async def test_get_config_returns_none_when_not_set() -> None:
    """Returns None when config not set."""
    provider = InMemoryTenantProvider()
    result = await provider.get_config("tenant-id", "key")
    assert result is None


@pytest.mark.asyncio
async def test_set_config_and_get_config() -> None:
    """Can set and retrieve config."""
    provider = InMemoryTenantProvider()
    await provider.set_config("tenant-id", "key", "value")
    result = await provider.get_config("tenant-id", "key")
    assert result == "value"


@pytest.mark.asyncio
async def test_get_all_config_returns_empty_when_none() -> None:
    """Returns empty dict when no config."""
    provider = InMemoryTenantProvider()
    result = await provider.get_all_config("tenant-id")
    assert result == {}


@pytest.mark.asyncio
async def test_get_all_config_returns_all_keys() -> None:
    """Returns all config keys."""
    provider = InMemoryTenantProvider()
    await provider.set_config("tenant-id", "key1", "value1")
    await provider.set_config("tenant-id", "key2", "value2")
    result = await provider.get_all_config("tenant-id")
    assert result == {"key1": "value1", "key2": "value2"}


@pytest.mark.asyncio
async def test_list_tenants_filters_inactive() -> None:
    """Does not return inactive tenants by default."""
    provider = InMemoryTenantProvider()
    result = await provider.create_tenant(
        CreateTenantCommand(slug="test", name="Test")
    )
    await provider.deactivate_tenant(result.unwrap().tenant_id)
    tenants = await provider.list_tenants(active_only=True)
    assert len(tenants) == 0


@pytest.mark.asyncio
async def test_create_tenant_with_plan() -> None:
    """Can create tenant with plan."""
    provider = InMemoryTenantProvider()
    result = await provider.create_tenant(
        CreateTenantCommand(slug="test", name="Test", plan="enterprise")
    )
    assert result.unwrap().plan == "enterprise"


@pytest.mark.asyncio
async def test_create_tenant_with_config() -> None:
    """Can create tenant with config."""
    provider = InMemoryTenantProvider()
    result = await provider.create_tenant(
        CreateTenantCommand(slug="test", name="Test", config={"max_users": 100})
    )
    assert result.unwrap().config == {"max_users": 100}


@pytest.mark.asyncio
async def test_update_tenant_partial() -> None:
    """Partial updates work (None fields skipped)."""
    provider = InMemoryTenantProvider()
    create_result = await provider.create_tenant(
        CreateTenantCommand(slug="test", name="Original", plan="basic")
    )
    tenant_id = create_result.unwrap().tenant_id
    result = await provider.update_tenant(
        tenant_id, UpdateTenantCommand(name="Updated")
    )
    assert result.unwrap().plan == "basic"
    assert result.unwrap().name == "Updated"


@pytest.mark.asyncio
async def test_create_tenant_with_metadata() -> None:
    """Can create tenant with metadata."""
    provider = InMemoryTenantProvider()
    result = await provider.create_tenant(
        CreateTenantCommand(slug="test", name="Test", metadata={"key": "value"})
    )
    assert result.unwrap().metadata == {"key": "value"}


@pytest.mark.asyncio
async def test_update_tenant_with_metadata() -> None:
    """Can update tenant with metadata."""
    provider = InMemoryTenantProvider()
    create_result = await provider.create_tenant(
        CreateTenantCommand(slug="test", name="Test")
    )
    tenant_id = create_result.unwrap().tenant_id
    result = await provider.update_tenant(
        tenant_id, UpdateTenantCommand(metadata={"new": "data"})
    )
    assert result.unwrap().metadata == {"new": "data"}


@pytest.mark.asyncio
async def test_get_tenant_by_slug_returns_correct_tenant() -> None:
    """Returns correct tenant when slug matches."""
    provider = InMemoryTenantProvider()
    await provider.create_tenant(
        CreateTenantCommand(slug="first", name="First")
    )
    await provider.create_tenant(
        CreateTenantCommand(slug="second", name="Second")
    )
    result = await provider.get_tenant_by_slug("second")
    assert result is not None
    assert result.slug == "second"


@pytest.mark.asyncio
async def test_list_tenants_includes_plan() -> None:
    """List includes plan field."""
    provider = InMemoryTenantProvider()
    await provider.create_tenant(
        CreateTenantCommand(slug="test", name="Test", plan="premium")
    )
    tenants = await provider.list_tenants()
    assert tenants[0].plan == "premium"