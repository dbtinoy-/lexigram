"""Database entity for admin users.

Provides the AdminUserEntity for database-backed user storage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from lexigram.admin.auth.user import AdminUserRecord


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(UTC)


@dataclass
class AdminUserEntity:
    """Database entity for admin users.

    Maps to the `admin_users` table.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    username: str = ""
    email: str = ""
    hashed_password: str = ""
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime | None = None

    def to_user(self) -> AdminUserRecord:
        """Convert entity to AdminUserRecord satisfying AuthenticatedUserProtocol protocol."""
        return AdminUserRecord(
            user_id=self.id,
            name=self.username,
            email=self.email,
            hashed_password=self.hashed_password,
            roles=self.roles,
            permissions=self.permissions,
            is_active=self.is_active,
            is_verified=self.is_verified,
        )

    @classmethod
    def from_user(cls, user: Any) -> AdminUserEntity:
        """Create entity from User dataclass."""
        return cls(
            id=user.user_id,
            username=user.name,
            email=user.email,
            hashed_password=user.hashed_password,
            roles=list(user.roles) if user.roles else [],
            permissions=list(user.permissions) if user.permissions else [],
            is_active=user.is_active,
            is_verified=user.is_verified,
        )
