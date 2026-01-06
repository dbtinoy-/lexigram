"""Membership entity and related domain events.

A :class:`Membership` associates a user with a :class:`~lexigram_example_platform.domain.tenant.Tenant`
and assigns them a :class:`Role`.  Membership events flow through the event bus
so that downstream systems (notifications, audit logs) can react without
coupling to this bounded context.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from lexigram.contracts.domain.events import DomainEvent
from lexigram.domain.models.entity import Entity


class Role(StrEnum):
    """Roles a member can hold within a tenant.

    Roles are ordered from most to least privileged::

        OWNER > ADMIN > MEMBER > VIEWER
    """

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


# ---------------------------------------------------------------------------
# Domain events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UserInvited(DomainEvent):
    """Emitted when a user is invited to join a tenant.

    Attributes:
        membership_id: Unique identifier of the new membership record.
        tenant_id: Tenant the user was invited to.
        user_id: Invited user's identifier.
        role: Role assigned at invitation time.
    """

    membership_id: str = ""
    tenant_id: str = ""
    user_id: str = ""
    role: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialise event to a plain dictionary.

        Returns:
            Dictionary including base event fields plus invitation-specific data.
        """
        return {
            **super().to_dict(),
            "membership_id": self.membership_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "role": self.role,
        }


@dataclass(frozen=True)
class RoleChanged(DomainEvent):
    """Emitted when an existing member's role is changed.

    Attributes:
        membership_id: Affected membership record identifier.
        tenant_id: Owning tenant identifier.
        user_id: User whose role was changed.
        old_role: Role before the change.
        new_role: Role after the change.
    """

    membership_id: str = ""
    tenant_id: str = ""
    user_id: str = ""
    old_role: str = ""
    new_role: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialise event to a plain dictionary.

        Returns:
            Dictionary including base event fields plus role-change data.
        """
        return {
            **super().to_dict(),
            "membership_id": self.membership_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "old_role": self.old_role,
            "new_role": self.new_role,
        }


# ---------------------------------------------------------------------------
# Entity
# ---------------------------------------------------------------------------


@dataclass
class Membership(Entity):
    """Entity representing a user's membership in a tenant.

    A membership record is the source of truth for which role a user holds
    within a specific tenant.  Equality is based on :attr:`id` (inherited
    from :class:`~lexigram.domain.models.entity.Entity`).

    Attributes:
        id: Unique membership identifier (UUID4 string).
        tenant_id: Owning tenant's identifier.
        user_id: Identifier of the member user.
        role: Current :class:`Role` held by the user.
        invited_at: UTC timestamp of the original invitation.
    """

    tenant_id: str = ""
    user_id: str = ""
    role: Role = Role.MEMBER
    invited_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def invite(cls, tenant_id: str, user_id: str, role: Role) -> Membership:
        """Create a new membership for an invited user.

        Args:
            tenant_id: Tenant the user is being invited to.
            user_id: Identifier of the invited user.
            role: Role to assign to the new member.

        Returns:
            A new :class:`Membership` instance with a generated identifier.
        """
        return cls(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
        )

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def change_role(self, new_role: Role) -> Role:
        """Change this member's role and return the previous role.

        Args:
            new_role: The role to assign.

        Returns:
            The previous role (useful for emitting :class:`RoleChanged`).

        Raises:
            ValueError: If ``new_role`` is the same as the current role.
        """
        if new_role == self.role:
            raise ValueError(
                f"Membership {self.id!r} already has role {self.role!r}."
            )
        old_role = self.role
        self.role = new_role
        return old_role

    def __repr__(self) -> str:
        return (
            f"Membership(id={self.id!r}, tenant_id={self.tenant_id!r}, "
            f"user_id={self.user_id!r}, role={self.role!r})"
        )


__all__ = [
    "Membership",
    "Role",
    "RoleChanged",
    "UserInvited",
]
