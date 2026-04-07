"""AdminUserAggregate — aggregate root for admin user management."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from lexigram.admin.events import (
    UserCreated,
    UserDeactivated,
    UserDeleted,
    UserUpdated,
)
from lexigram.domain.models.aggregate import AggregateRoot


@dataclass
class AdminUserAggregate(AggregateRoot):
    """Aggregate root representing an admin-managed user.

    Encapsulates all state transitions for a user managed through the
    admin panel, recording domain events on each mutation.
    """

    username: str = ""
    email: str = ""
    hashed_password: str = ""
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    is_active: bool = True
    deleted_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        user_id: str,
        username: str,
        email: str,
        hashed_password: str,
        roles: list[str] | None = None,
        permissions: list[str] | None = None,
        actor_id: str = "",
    ) -> AdminUserAggregate:
        """Create a new AdminUserAggregate and record a UserCreated event.

        Args:
            user_id: Unique identifier for the user.
            username: Login username.
            email: Email address.
            hashed_password: Pre-hashed password string.
            roles: Initial role assignments.
            permissions: Initial permission grants.
            actor_id: Identity of the principal performing the action.

        Returns:
            A fully initialised aggregate with one pending domain event.
        """
        aggregate = cls(
            id=user_id,
            username=username,
            email=email,
            hashed_password=hashed_password,
            roles=roles or [],
            permissions=permissions or [],
        )
        aggregate._record_event(
            UserCreated(
                user_id=user_id,
                email=email,
                actor_id=actor_id or None,
            )
        )
        return aggregate

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def update(self, changes: dict[str, Any], actor_id: str = "") -> None:
        """Apply a partial update and record a UserUpdated event.

        Args:
            changes: Mapping of field names to new values.
            actor_id: Identity of the principal performing the action.
        """
        for key, value in changes.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self._record_event(
            UserUpdated(
                user_id=str(self.id),
                changes=changes,
                actor_id=actor_id or None,
            )
        )

    def deactivate(self, actor_id: str = "") -> None:
        """Deactivate this user and record a UserDeactivated event.

        Args:
            actor_id: Identity of the principal performing the action.
        """
        self.is_active = False
        self._record_event(
            UserDeactivated(
                user_id=str(self.id),
                actor_id=actor_id or None,
            )
        )

    def soft_delete(self, actor_id: str = "") -> None:
        """Soft-delete this user and record a UserDeleted event.

        Sets ``deleted_at`` to now and ``is_active`` to False.

        Args:
            actor_id: Identity of the principal performing the action.
        """
        self.deleted_at = datetime.now(UTC)
        self.is_active = False
        self._record_event(
            UserDeleted(
                user_id=str(self.id),
                actor_id=actor_id or None,
            )
        )
