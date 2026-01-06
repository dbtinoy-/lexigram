"""Membership application service.

:class:`MembershipService` implements the use-cases for managing
:class:`~lexigram_example_platform.domain.membership.Membership` entities:
inviting users and changing their role within a tenant.

Every public method returns ``Result[T, DomainError]``.  Callers must check
``is_ok()`` before calling ``unwrap()``.  The service never raises
``DomainError`` — all expected failure paths are expressed as ``Err`` values.

Dependency injection
--------------------
All dependencies are received via ``__init__`` (constructor injection). The
container resolves and passes them; this class never touches the container.
"""

from __future__ import annotations

from lexigram.contracts.events.protocols import EventBusProtocol
from lexigram.contracts.exceptions.domain import ConflictError, DomainError, NotFoundError
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

from lexigram_example_platform.domain.membership import Membership, Role, RoleChanged, UserInvited
from lexigram_example_platform.repositories.membership_repository import (
    MembershipRepositoryProtocol,
)
from lexigram_example_platform.repositories.tenant_repository import (
    TenantRepositoryProtocol,
)

logger = get_logger(__name__)


class MembershipService:
    """Use-case handler for membership operations within a tenant.

    Coordinates between :class:`~lexigram_example_platform.domain.membership.Membership`
    entities, tenant and membership repositories, and the event bus.

    Args:
        repo: Repository for loading and persisting memberships.
        tenant_repo: Repository for verifying tenant existence.
        event_bus: Event bus for dispatching domain events after mutations.
    """

    def __init__(
        self,
        repo: MembershipRepositoryProtocol,
        tenant_repo: TenantRepositoryProtocol,
        event_bus: EventBusProtocol,
    ) -> None:
        self._repo = repo
        self._tenant_repo = tenant_repo
        self._event_bus = event_bus

    async def invite_user(
        self,
        tenant_id: str,
        user_id: str,
        role: Role = Role.MEMBER,
    ) -> Result[Membership, DomainError]:
        """Invite a user to a tenant with the specified role.

        Validates that the tenant exists and the user is not already a member
        before creating the membership record.

        Args:
            tenant_id: Owning tenant's unique identifier.
            user_id: Identifier of the user being invited.
            role: Role to assign.  Defaults to :attr:`~Role.MEMBER`.

        Returns:
            ``Ok(Membership)`` on success; ``Err(NotFoundError)`` when the
            tenant does not exist; ``Err(ConflictError)`` when the user is
            already a member.
        """
        tenant = await self._tenant_repo.get(tenant_id)
        if tenant is None:
            return Err(NotFoundError(f"Tenant {tenant_id!r} not found."))

        if not tenant.is_active:
            return Err(
                DomainError(
                    f"Cannot invite to suspended tenant {tenant_id!r}.",
                    details={"tenant_id": tenant_id},
                )
            )

        existing = await self._repo.find_by_tenant_and_user(tenant_id, user_id)
        if existing is not None:
            return Err(
                ConflictError(
                    f"User {user_id!r} is already a member of tenant {tenant_id!r}.",
                    details={"tenant_id": tenant_id, "user_id": user_id},
                )
            )

        membership = Membership.invite(
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
        )

        await self._repo.save(membership)

        event = UserInvited(
            membership_id=membership.id,
            tenant_id=tenant_id,
            user_id=user_id,
            role=role.value,
        )
        await self._publish_event(event)

        logger.info(
            "membership_service.user_invited",
            membership_id=membership.id,
            tenant_id=tenant_id,
            user_id=user_id,
            role=role.value,
        )
        return Ok(membership)

    async def change_role(
        self,
        membership_id: str,
        new_role: Role,
    ) -> Result[Membership, DomainError]:
        """Change the role of an existing membership.

        Args:
            membership_id: Unique identifier of the membership to update.
            new_role: The :class:`~Role` to assign.

        Returns:
            ``Ok(Membership)`` with the updated entity on success;
            ``Err(NotFoundError)`` when the membership does not exist;
            ``Err(DomainError)`` when the role is unchanged.
        """
        membership = await self._repo.get(membership_id)
        if membership is None:
            return Err(
                NotFoundError(f"Membership {membership_id!r} not found.")
            )

        if membership.role == new_role:
            return Err(
                DomainError(
                    f"Membership {membership_id!r} already has role {new_role!r}.",
                    details={"membership_id": membership_id, "role": new_role},
                )
            )

        old_role = membership.change_role(new_role)

        await self._repo.save(membership)

        event = RoleChanged(
            membership_id=membership.id,
            tenant_id=membership.tenant_id,
            user_id=membership.user_id,
            old_role=old_role.value,
            new_role=new_role.value,
        )
        await self._publish_event(event)

        logger.info(
            "membership_service.role_changed",
            membership_id=membership_id,
            old_role=old_role.value,
            new_role=new_role.value,
        )
        return Ok(membership)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _publish_event(self, event: object) -> None:
        """Publish a domain event, logging but not re-raising on failure.

        Args:
            event: The domain event to publish.
        """
        result = await self._event_bus.publish(event)
        if result.is_err():
            logger.warning(
                "membership_service.event_dispatch_failed",
                event_type=type(event).__name__,
                error=str(result.unwrap_err()),
            )


__all__ = ["MembershipService"]
