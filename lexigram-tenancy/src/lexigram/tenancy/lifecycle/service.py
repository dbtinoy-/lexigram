"""Tenant lifecycle service — CRUD, events, and validator invalidation."""

from __future__ import annotations

from datetime import UTC, datetime

from lexigram.contracts.events.protocols import DomainEventPublisherProtocol
from lexigram.contracts.tenancy.commands import CreateTenantCommand, UpdateTenantCommand
from lexigram.contracts.tenancy.errors import TenantError, TenantSlugConflictError
from lexigram.contracts.tenancy.events import (
    TenantActivated,
    TenantDeactivated,
    TenantProvisioned,
    TenantSuspended,
)
from lexigram.contracts.tenancy.protocols import TenantProviderProtocol
from lexigram.contracts.tenancy.types import TenantInfo
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result
from lexigram.tenancy.enforcement.validator import TenantValidator
from lexigram.tenancy.lifecycle.provisioner import TenantProvisioner

logger = get_logger(__name__)


class TenantLifecycleService:
    """Orchestrates tenant CRUD operations with event emission and cache invalidation.

    All mutations publish the corresponding domain event via the event bus
    and invalidate the :class:`~lexigram.tenancy.enforcement.validator.TenantValidator`
    cache so subsequent requests see fresh state.

    Usage::

        service = TenantLifecycleService(provider, provisioner, event_bus, validator)
        result = await service.create_tenant(CreateTenantCommand(slug="acme", name="ACME Corp"))
        if result.is_ok():
            tenant = result.unwrap()
    """

    def __init__(
        self,
        provider: TenantProviderProtocol,
        provisioner: TenantProvisioner,
        event_bus: DomainEventPublisherProtocol,
        validator: TenantValidator,
    ) -> None:
        """Initialise the service.

        Args:
            provider: Tenant storage backend.
            provisioner: Isolation provisioner for new/removed tenants.
            event_bus: Event bus for publishing domain events.
            validator: Validator cache to invalidate on mutations.
        """
        self._provider = provider
        self._provisioner = provisioner
        self._event_bus = event_bus
        self._validator = validator

    async def create_tenant(
        self, command: CreateTenantCommand
    ) -> Result[TenantInfo, TenantError]:
        """Create a new tenant, provision isolation, and publish the event.

        Args:
            command: Tenant creation parameters.

        Returns:
            ``Ok(TenantInfo)`` on success, ``Err(TenantError)`` on failure.
        """
        existing = await self._provider.get_tenant_by_slug(command.slug)
        if existing is not None:
            return Err(TenantSlugConflictError(command.slug))

        result = await self._provider.create_tenant(command)
        if result.is_err():
            return result

        tenant = result.unwrap()

        provision_result = await self._provisioner.provision(tenant.tenant_id)
        if provision_result.is_err():
            logger.error("tenant_provisioning_failed", tenant_id=tenant.tenant_id)
            return Err(provision_result.unwrap_err())

        await self._event_bus.publish(
            TenantProvisioned(
                tenant_id=tenant.tenant_id,
                slug=tenant.slug,
                plan=tenant.plan,
                timestamp=datetime.now(UTC),
            )
        )
        logger.info("tenant_created", tenant_id=tenant.tenant_id, slug=tenant.slug)
        return Ok(tenant)

    async def update_tenant(
        self, tenant_id: str, command: UpdateTenantCommand
    ) -> Result[TenantInfo, TenantError]:
        """Update a tenant's mutable fields.

        Args:
            tenant_id: Identifier of the tenant to update.
            command: Fields to apply.

        Returns:
            ``Ok(TenantInfo)`` with the updated record, ``Err(TenantError)`` on failure.
        """
        result = await self._provider.update_tenant(tenant_id, command)
        if result.is_ok():
            self._validator.invalidate(tenant_id)
        return result

    async def deactivate_tenant(self, tenant_id: str) -> Result[None, TenantError]:
        """Deactivate a tenant and publish the event.

        Args:
            tenant_id: Identifier of the tenant to deactivate.

        Returns:
            ``Ok(None)`` on success, ``Err(TenantError)`` on failure.
        """
        result = await self._provider.deactivate_tenant(tenant_id)
        if result.is_ok():
            self._validator.invalidate(tenant_id)
            await self._event_bus.publish(
                TenantDeactivated(
                    tenant_id=tenant_id,
                    timestamp=datetime.now(UTC),
                )
            )
            logger.info("tenant_deactivated", tenant_id=tenant_id)
        return result

    async def activate_tenant(self, tenant_id: str) -> Result[None, TenantError]:
        """Activate a tenant and publish the event.

        Args:
            tenant_id: Identifier of the tenant to activate.

        Returns:
            ``Ok(None)`` on success, ``Err(TenantError)`` on failure.
        """
        result = await self._provider.activate_tenant(tenant_id)
        if result.is_ok():
            self._validator.invalidate(tenant_id)
            await self._event_bus.publish(
                TenantActivated(
                    tenant_id=tenant_id,
                    timestamp=datetime.now(UTC),
                )
            )
            logger.info("tenant_activated", tenant_id=tenant_id)
        return result

    async def suspend_tenant(
        self, tenant_id: str, reason: str | None = None
    ) -> Result[None, TenantError]:
        """Suspend a tenant and publish the event.

        Args:
            tenant_id: Identifier of the tenant to suspend.
            reason: Optional reason for the suspension.

        Returns:
            ``Ok(None)`` on success, ``Err(TenantError)`` on failure.
        """
        result = await self._provider.suspend_tenant(tenant_id, reason)
        if result.is_ok():
            self._validator.invalidate(tenant_id)
            await self._event_bus.publish(
                TenantSuspended(
                    tenant_id=tenant_id,
                    reason=reason,
                    timestamp=datetime.now(UTC),
                )
            )
            logger.info("tenant_suspended", tenant_id=tenant_id)
        return result


__all__ = ["TenantLifecycleService"]
