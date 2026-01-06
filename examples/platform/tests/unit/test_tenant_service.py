"""Unit tests for TenantService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.result import Ok
from lexigram_example_platform.domain.tenant import Tenant, TenantStatus
from lexigram_example_platform.repositories.tenant_repository import (
    InMemoryTenantRepository,
)
from lexigram_example_platform.services.tenant_service import TenantService


def _make_event_bus() -> MagicMock:
    bus = MagicMock()
    bus.publish = AsyncMock(return_value=Ok(None))
    return bus


def _make_service(
    repo: InMemoryTenantRepository | None = None,
) -> tuple[TenantService, InMemoryTenantRepository]:
    repo = repo or InMemoryTenantRepository()
    service = TenantService(repo=repo, event_bus=_make_event_bus())
    return service, repo


class TestCreateTenant:
    """Tests for TenantService.create_tenant()."""

    @pytest.mark.asyncio
    async def test_creates_active_tenant(self):
        """create_tenant returns Ok(Tenant) with ACTIVE status."""
        service, repo = _make_service()

        result = await service.create_tenant(name="Acme Corp", slug="acme")

        assert result.is_ok()
        tenant = result.unwrap()
        assert tenant.name == "Acme Corp"
        assert tenant.slug == "acme"
        assert tenant.status == TenantStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_persists_tenant(self):
        """Tenant is stored in the repository after creation."""
        service, repo = _make_service()

        result = await service.create_tenant(name="Example", slug="example")

        assert result.is_ok()
        tenant_id = result.unwrap().id
        stored = await repo.get(tenant_id)
        assert stored is not None
        assert stored.slug == "example"

    @pytest.mark.asyncio
    async def test_slug_conflict_returns_err(self):
        """create_tenant returns Err(ConflictError) when slug is already taken."""
        service, _ = _make_service()
        await service.create_tenant(name="First", slug="taken")

        result = await service.create_tenant(name="Second", slug="taken")

        assert result.is_err()
        from lexigram.contracts.exceptions.domain import ConflictError
        assert isinstance(result.unwrap_err(), ConflictError)

    @pytest.mark.asyncio
    async def test_empty_name_returns_err(self):
        """create_tenant returns Err when name is blank."""
        service, _ = _make_service()

        result = await service.create_tenant(name="   ", slug="valid-slug")

        assert result.is_err()

    @pytest.mark.asyncio
    async def test_empty_slug_returns_err(self):
        """create_tenant returns Err when slug is blank."""
        service, _ = _make_service()

        result = await service.create_tenant(name="Valid Name", slug="")

        assert result.is_err()

    @pytest.mark.asyncio
    async def test_domain_event_dispatched_on_creation(self):
        """TenantCreated event is dispatched to the event bus."""
        bus = _make_event_bus()
        repo = InMemoryTenantRepository()
        service = TenantService(repo=repo, event_bus=bus)

        await service.create_tenant(name="Event Corp", slug="event")

        bus.publish.assert_awaited_once()
        event = bus.publish.call_args[0][0]
        assert event.__class__.__name__ == "TenantCreated"


class TestSuspendTenant:
    """Tests for TenantService.suspend_tenant()."""

    @pytest.mark.asyncio
    async def test_suspends_active_tenant(self):
        """suspend_tenant returns Ok(Tenant) with SUSPENDED status."""
        service, repo = _make_service()
        create_result = await service.create_tenant(name="Suspend Me", slug="suspend")
        tenant_id = create_result.unwrap().id

        result = await service.suspend_tenant(tenant_id, reason="violation")

        assert result.is_ok()
        tenant = result.unwrap()
        assert tenant.status == TenantStatus.SUSPENDED

    @pytest.mark.asyncio
    async def test_not_found_returns_err(self):
        """suspend_tenant returns Err(NotFoundError) for unknown tenant."""
        service, _ = _make_service()

        result = await service.suspend_tenant("nonexistent-id")

        assert result.is_err()
        from lexigram.contracts.exceptions.domain import NotFoundError
        assert isinstance(result.unwrap_err(), NotFoundError)

    @pytest.mark.asyncio
    async def test_double_suspend_returns_err(self):
        """suspend_tenant returns Err when tenant is already suspended."""
        service, _ = _make_service()
        result = await service.create_tenant(name="Dbl", slug="dbl")
        tenant_id = result.unwrap().id

        await service.suspend_tenant(tenant_id)
        result2 = await service.suspend_tenant(tenant_id)

        assert result2.is_err()

    @pytest.mark.asyncio
    async def test_suspension_event_dispatched(self):
        """TenantSuspended event is published when suspending a tenant."""
        bus = _make_event_bus()
        repo = InMemoryTenantRepository()
        service = TenantService(repo=repo, event_bus=bus)

        create_result = await service.create_tenant(name="Evt", slug="evt")
        tenant_id = create_result.unwrap().id
        bus.publish.reset_mock()

        await service.suspend_tenant(tenant_id, reason="test")

        bus.publish.assert_awaited_once()
        event = bus.publish.call_args[0][0]
        assert event.__class__.__name__ == "TenantSuspended"


__all__: list[str] = []
