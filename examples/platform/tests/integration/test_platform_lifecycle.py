"""Integration tests: full platform tenant lifecycle.

Tests the end-to-end flow of tenant provisioning, member invitation,
role changes, and suspension using only in-memory implementations.
No real database or event bus is required.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.result import Ok
from lexigram_example_platform.domain.membership import Role
from lexigram_example_platform.domain.policy import can_access
from lexigram_example_platform.domain.tenant import TenantStatus
from lexigram_example_platform.repositories.membership_repository import (
    InMemoryMembershipRepository,
)
from lexigram_example_platform.repositories.tenant_repository import (
    InMemoryTenantRepository,
)
from lexigram_example_platform.services.membership_service import MembershipService
from lexigram_example_platform.services.tenant_service import TenantService


def _make_event_bus() -> MagicMock:
    bus = MagicMock()
    bus.publish = AsyncMock(return_value=Ok(None))
    return bus


@pytest.fixture()
def tenant_repo():
    return InMemoryTenantRepository()


@pytest.fixture()
def membership_repo():
    return InMemoryMembershipRepository()


@pytest.fixture()
def event_bus():
    return _make_event_bus()


@pytest.fixture()
def tenant_service(tenant_repo, event_bus):
    return TenantService(repo=tenant_repo, event_bus=event_bus)


@pytest.fixture()
def membership_service(membership_repo, tenant_repo, event_bus):
    return MembershipService(
        repo=membership_repo,
        tenant_repo=tenant_repo,
        event_bus=event_bus,
    )


@pytest.mark.asyncio
async def test_full_tenant_provisioning_lifecycle(
    tenant_service, tenant_repo, event_bus
):
    """Tenant is created, persisted, retrievable by slug, and emits events."""
    result = await tenant_service.create_tenant(name="Acme SaaS", slug="acme-saas")

    assert result.is_ok()
    tenant = result.unwrap()
    assert tenant.status == TenantStatus.ACTIVE

    # Verify persistence
    from_repo = await tenant_repo.get(tenant.id)
    assert from_repo is not None
    assert from_repo.slug == "acme-saas"

    by_slug = await tenant_repo.find_by_slug("acme-saas")
    assert by_slug is not None
    assert by_slug.id == tenant.id

    # Verify event
    event_bus.publish.assert_awaited_once()
    assert event_bus.publish.call_args[0][0].__class__.__name__ == "TenantCreated"


@pytest.mark.asyncio
async def test_tenant_invite_and_role_upgrade(
    tenant_service, membership_service, membership_repo, event_bus
):
    """Users can be invited and promoted through the role hierarchy."""
    # Create tenant
    t_result = await tenant_service.create_tenant(name="Multi Corp", slug="multi-corp")
    tenant = t_result.unwrap()

    # Invite owner
    owner_result = await membership_service.invite_user(
        tenant_id=tenant.id, user_id="owner-1", role=Role.OWNER
    )
    assert owner_result.is_ok()

    # Invite viewer and promote to admin
    viewer_result = await membership_service.invite_user(
        tenant_id=tenant.id, user_id="viewer-1", role=Role.VIEWER
    )
    membership_id = viewer_result.unwrap().id
    event_bus.publish.reset_mock()

    promote_result = await membership_service.change_role(membership_id, Role.ADMIN)
    assert promote_result.is_ok()
    assert promote_result.unwrap().role == Role.ADMIN

    # Check event
    event_bus.publish.assert_awaited_once()
    assert event_bus.publish.call_args[0][0].__class__.__name__ == "RoleChanged"

    # Verify RBAC is respected for new role
    assert can_access(Role.ADMIN, "users", "write") is True
    assert can_access(Role.VIEWER, "users", "write") is False


@pytest.mark.asyncio
async def test_tenant_suspension_blocks_new_invitations(
    tenant_service, membership_service
):
    """Once suspended, a tenant cannot accept new member invitations."""
    t_result = await tenant_service.create_tenant(
        name="Suspended Corp", slug="suspended-corp"
    )
    tenant = t_result.unwrap()

    # Suspend the tenant
    suspend_result = await tenant_service.suspend_tenant(tenant.id, reason="policy")
    assert suspend_result.is_ok()
    assert suspend_result.unwrap().status == TenantStatus.SUSPENDED

    # Invitation should fail
    invite_result = await membership_service.invite_user(
        tenant_id=tenant.id, user_id="late-user"
    )
    assert invite_result.is_err()


@pytest.mark.asyncio
async def test_multiple_tenants_are_isolated(tenant_service, membership_service):
    """Members of one tenant are not visible from another tenant."""
    t1 = (await tenant_service.create_tenant(name="Tenant A", slug="tenant-a")).unwrap()
    t2 = (await tenant_service.create_tenant(name="Tenant B", slug="tenant-b")).unwrap()

    await membership_service.invite_user(tenant_id=t1.id, user_id="shared-user")
    await membership_service.invite_user(tenant_id=t2.id, user_id="shared-user")

    # Both memberships exist independently
    from lexigram_example_platform.repositories.membership_repository import (
        InMemoryMembershipRepository,
    )
    t1_member_result = await membership_service._repo.find_by_tenant_and_user(
        t1.id, "shared-user"
    )
    t2_member_result = await membership_service._repo.find_by_tenant_and_user(
        t2.id, "shared-user"
    )
    assert t1_member_result is not None
    assert t2_member_result is not None
    assert t1_member_result.id != t2_member_result.id


@pytest.mark.asyncio
async def test_slug_uniqueness_is_enforced(tenant_service):
    """Two tenants cannot share the same slug."""
    await tenant_service.create_tenant(name="First", slug="unique-slug")
    result = await tenant_service.create_tenant(name="Second", slug="unique-slug")

    assert result.is_err()
    from lexigram.contracts.exceptions.domain import ConflictError
    assert isinstance(result.unwrap_err(), ConflictError)


__all__: list[str] = []
