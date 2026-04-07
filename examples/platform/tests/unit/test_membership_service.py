"""Unit tests for MembershipService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.result import Ok
from lexigram_example_platform.domain.membership import Membership, Role
from lexigram_example_platform.domain.tenant import Tenant, TenantStatus
from lexigram_example_platform.repositories.membership_repository import (
    InMemoryMembershipRepository,
)
from lexigram_example_platform.repositories.tenant_repository import (
    InMemoryTenantRepository,
)
from lexigram_example_platform.services.membership_service import MembershipService


def _make_event_bus() -> MagicMock:
    bus = MagicMock()
    bus.publish = AsyncMock(return_value=Ok(None))
    return bus


async def _seed_tenant(
    tenant_repo: InMemoryTenantRepository,
    status: TenantStatus = TenantStatus.ACTIVE,
) -> Tenant:
    """Insert a test tenant into *tenant_repo* and return it."""
    tenant = Tenant.create(name="Test Corp", slug="test-corp")
    if status == TenantStatus.SUSPENDED:
        tenant.suspend(reason="test seed")
    await tenant_repo.save(tenant)
    return tenant


def _make_service() -> tuple[MembershipService, InMemoryMembershipRepository, InMemoryTenantRepository]:
    tenant_repo = InMemoryTenantRepository()
    membership_repo = InMemoryMembershipRepository()
    service = MembershipService(
        repo=membership_repo,
        tenant_repo=tenant_repo,
        event_bus=_make_event_bus(),
    )
    return service, membership_repo, tenant_repo


class TestInviteUser:
    """Tests for MembershipService.invite_user()."""

    @pytest.mark.asyncio
    async def test_invites_user_to_active_tenant(self):
        """invite_user returns Ok(Membership) for a valid invitation."""
        service, _, tenant_repo = _make_service()
        tenant = await _seed_tenant(tenant_repo)

        result = await service.invite_user(
            tenant_id=tenant.id, user_id="user-1", role=Role.MEMBER
        )

        assert result.is_ok()
        membership = result.unwrap()
        assert isinstance(membership, Membership)
        assert membership.tenant_id == tenant.id
        assert membership.user_id == "user-1"
        assert membership.role == Role.MEMBER

    @pytest.mark.asyncio
    async def test_tenant_not_found_returns_err(self):
        """invite_user returns Err(NotFoundError) for an unknown tenant."""
        service, _, _ = _make_service()

        result = await service.invite_user(
            tenant_id="ghost-id", user_id="user-1"
        )

        assert result.is_err()
        from lexigram.contracts.exceptions.domain import NotFoundError
        assert isinstance(result.unwrap_err(), NotFoundError)

    @pytest.mark.asyncio
    async def test_suspended_tenant_returns_err(self):
        """invite_user returns Err when tenant is suspended."""
        service, _, tenant_repo = _make_service()
        tenant = await _seed_tenant(tenant_repo, status=TenantStatus.SUSPENDED)

        result = await service.invite_user(
            tenant_id=tenant.id, user_id="user-1"
        )

        assert result.is_err()

    @pytest.mark.asyncio
    async def test_duplicate_membership_returns_err(self):
        """invite_user returns Err(ConflictError) when user is already a member."""
        service, _, tenant_repo = _make_service()
        tenant = await _seed_tenant(tenant_repo)

        await service.invite_user(tenant_id=tenant.id, user_id="user-dup")
        result = await service.invite_user(tenant_id=tenant.id, user_id="user-dup")

        assert result.is_err()
        from lexigram.contracts.exceptions.domain import ConflictError
        assert isinstance(result.unwrap_err(), ConflictError)

    @pytest.mark.asyncio
    async def test_user_invited_event_dispatched(self):
        """UserInvited event is published after a successful invitation."""
        bus = _make_event_bus()
        tenant_repo = InMemoryTenantRepository()
        membership_repo = InMemoryMembershipRepository()
        service = MembershipService(
            repo=membership_repo, tenant_repo=tenant_repo, event_bus=bus
        )
        tenant = await _seed_tenant(tenant_repo)

        await service.invite_user(tenant_id=tenant.id, user_id="event-user")

        bus.publish.assert_awaited_once()
        event = bus.publish.call_args[0][0]
        assert event.__class__.__name__ == "UserInvited"


class TestChangeRole:
    """Tests for MembershipService.change_role()."""

    @pytest.mark.asyncio
    async def test_changes_member_role(self):
        """change_role returns Ok(Membership) with the updated role."""
        service, membership_repo, tenant_repo = _make_service()
        tenant = await _seed_tenant(tenant_repo)
        invite_result = await service.invite_user(
            tenant_id=tenant.id, user_id="promo-user", role=Role.MEMBER
        )
        membership_id = invite_result.unwrap().id

        result = await service.change_role(membership_id, Role.ADMIN)

        assert result.is_ok()
        assert result.unwrap().role == Role.ADMIN

    @pytest.mark.asyncio
    async def test_membership_not_found_returns_err(self):
        """change_role returns Err(NotFoundError) for an unknown membership."""
        service, _, _ = _make_service()

        result = await service.change_role("ghost-membership", Role.ADMIN)

        assert result.is_err()
        from lexigram.contracts.exceptions.domain import NotFoundError
        assert isinstance(result.unwrap_err(), NotFoundError)

    @pytest.mark.asyncio
    async def test_same_role_returns_err(self):
        """change_role returns Err when the new role equals the current role."""
        service, _, tenant_repo = _make_service()
        tenant = await _seed_tenant(tenant_repo)
        invite_result = await service.invite_user(
            tenant_id=tenant.id, user_id="same-role-user", role=Role.MEMBER
        )
        membership_id = invite_result.unwrap().id

        result = await service.change_role(membership_id, Role.MEMBER)

        assert result.is_err()

    @pytest.mark.asyncio
    async def test_role_changed_event_dispatched(self):
        """RoleChanged event is dispatched after a successful role change."""
        bus = _make_event_bus()
        tenant_repo = InMemoryTenantRepository()
        membership_repo = InMemoryMembershipRepository()
        service = MembershipService(
            repo=membership_repo, tenant_repo=tenant_repo, event_bus=bus
        )
        tenant = await _seed_tenant(tenant_repo)
        invite_result = await service.invite_user(
            tenant_id=tenant.id, user_id="role-evt-user", role=Role.MEMBER
        )
        membership_id = invite_result.unwrap().id
        bus.publish.reset_mock()

        await service.change_role(membership_id, Role.ADMIN)

        bus.publish.assert_awaited_once()
        event = bus.publish.call_args[0][0]
        assert event.__class__.__name__ == "RoleChanged"


__all__: list[str] = []
