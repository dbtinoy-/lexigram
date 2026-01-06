"""Tenant application service.

:class:`TenantService` implements the use-cases that mutate
:class:`~lexigram_example_platform.domain.tenant.Tenant` aggregates.

Every public method returns ``Result[T, DomainError]``.  Callers must check
``is_ok()`` before calling ``unwrap()``.  The service never raises
``DomainError`` — all expected failure paths are expressed as ``Err`` values.

Dependency injection
--------------------
All dependencies are received via ``__init__`` (constructor injection). The
container resolves and passes them; this class never touches the container.
"""

from __future__ import annotations

from lexigram.contracts.domain.events import DomainEvent
from lexigram.contracts.events.protocols import EventBusProtocol
from lexigram.contracts.exceptions.domain import ConflictError, DomainError, NotFoundError
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

from lexigram_example_platform.domain.tenant import Tenant, TenantStatus
from lexigram_example_platform.repositories.tenant_repository import (
    TenantRepositoryProtocol,
)

logger = get_logger(__name__)


class TenantService:
    """Use-case handler for tenant lifecycle operations.

    Coordinates between the :class:`~lexigram_example_platform.domain.tenant.Tenant`
    aggregate, the repository, and the event bus.  Business logic stays in
    the aggregate; orchestration lives here.

    Args:
        repo: Repository for loading and persisting tenants.
        event_bus: Event bus for dispatching domain events after state changes.
    """

    def __init__(
        self,
        repo: TenantRepositoryProtocol,
        event_bus: EventBusProtocol,
    ) -> None:
        self._repo = repo
        self._event_bus = event_bus

    async def create_tenant(
        self,
        name: str,
        slug: str,
    ) -> Result[Tenant, DomainError]:
        """Provision a new tenant with the given name and slug.

        Checks that the slug is not already taken before saving.  On success,
        all buffered domain events are dispatched to the event bus.

        Args:
            name: Human-readable display name.  Must be non-empty.
            slug: URL-safe, lowercase, hyphen-separated unique identifier.

        Returns:
            ``Ok(Tenant)`` on success; ``Err(DomainError)`` when validation
            fails or the slug is already in use.
        """
        if not name or not name.strip():
            return Err(DomainError("Tenant name must not be empty."))

        if not slug or not slug.strip():
            return Err(DomainError("Tenant slug must not be empty."))

        existing = await self._repo.find_by_slug(slug)
        if existing is not None:
            return Err(
                ConflictError(
                    f"Slug {slug!r} is already taken.",
                    details={"slug": slug},
                )
            )

        tenant = Tenant.create(name=name.strip(), slug=slug.strip())

        await self._repo.save(tenant)

        await self._dispatch_events(tenant.collect_events())

        logger.info("tenant_service.tenant_created", tenant_id=tenant.id, slug=slug)
        return Ok(tenant)

    async def suspend_tenant(
        self,
        tenant_id: str,
        reason: str = "",
    ) -> Result[Tenant, DomainError]:
        """Suspend an active tenant.

        Args:
            tenant_id: Unique identifier of the tenant to suspend.
            reason: Human-readable explanation for the suspension.

        Returns:
            ``Ok(Tenant)`` with the updated aggregate; ``Err(NotFoundError)``
            when the tenant does not exist; ``Err(DomainError)`` when the
            tenant is already suspended.
        """
        tenant = await self._repo.get(tenant_id)
        if tenant is None:
            return Err(NotFoundError(f"Tenant {tenant_id!r} not found."))

        if tenant.status == TenantStatus.SUSPENDED:
            return Err(
                DomainError(
                    f"Tenant {tenant_id!r} is already suspended.",
                    details={"tenant_id": tenant_id},
                )
            )

        tenant.suspend(reason=reason)

        await self._repo.save(tenant)

        await self._dispatch_events(tenant.collect_events())

        logger.info(
            "tenant_service.tenant_suspended",
            tenant_id=tenant_id,
            reason=reason,
        )
        return Ok(tenant)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _dispatch_events(self, events: list[DomainEvent]) -> None:
        """Publish all domain events to the event bus.

        Publication failures are logged but do not abort the use-case —
        the state change is already persisted.

        Args:
            events: Events to publish.
        """
        for event in events:
            result = await self._event_bus.publish(event)
            if result.is_err():
                logger.warning(
                    "tenant_service.event_dispatch_failed",
                    event_type=type(event).__name__,
                    error=str(result.unwrap_err()),
                )


__all__ = ["TenantService"]
