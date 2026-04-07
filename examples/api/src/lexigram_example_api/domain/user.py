"""User domain entity and related events.

The ``User`` entity is the aggregate root for the identity bounded context.
It carries only the data required by the application domain — credentials
(hashed) are stored on the entity so the repository owns all user state.

Domain events raised by user operations:
- :class:`UserCreated` — emitted after successful registration.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from lexigram.contracts.domain import DomainEvent


# ---------------------------------------------------------------------------
# Domain events
# ---------------------------------------------------------------------------


class UserCreated(DomainEvent):
    """Raised when a new user account is created.

    Attributes:
        user_id: Stable identifier of the new user.
        email: Email address used at registration.
    """

    def __init__(self, *, user_id: str, email: str, **kwargs: object) -> None:
        """Initialise the event.

        Args:
            user_id: The new user's identifier.
            email: The registration email address.
            **kwargs: Forwarded to :class:`~lexigram.contracts.domain.DomainEvent`.
        """
        super().__init__(user_id=user_id, email=email, **kwargs)


# ---------------------------------------------------------------------------
# Domain entity
# ---------------------------------------------------------------------------


@dataclass
class User:
    """User entity — the root aggregate for the identity context.

    This is a plain dataclass (not a Pydantic model) so it has no
    serialisation magic; controllers produce response dicts explicitly.
    Keeping it infrastructure-free makes it trivially testable and cheap
    to construct in tests.

    Attributes:
        user_id: Stable UUID string identifier.
        email: Unique email address.
        hashed_password: Bcrypt-hashed password — never returned to callers.
        is_active: Whether the account is active.
        created_at: UTC timestamp of account creation.
    """

    user_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    email: str = ""
    hashed_password: str = ""
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_public_dict(self) -> dict[str, object]:
        """Return a public-safe representation (no password hash).

        Returns:
            Dict with ``user_id``, ``email``, ``is_active``, ``created_at``.
        """
        return {
            "user_id": self.user_id,
            "email": self.email,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }
