"""Auth integration for lexigram-admin.

This module provides the ``AdminUser`` dataclass — the primary admin user
representation that satisfies ``AuthenticatedUserProtocol`` — plus re-exports
of relevant contracts types for consumer convenience.

CROSS-EXT-02: Uses protocols from lexigram-contracts for dependency injection,
eliminating direct cross-extension imports from lexigram-auth.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lexigram.contracts import AuthenticatedUserProtocol as AuthenticatedUserProtocol
from lexigram.contracts.auth import PasswordHasherProtocol

# ============================================================================
# Admin User
# ============================================================================


@dataclass
class AdminUser:
    """Admin user implementing AuthenticatedUserProtocol protocol.

    This class represents an authenticated admin user with
    roles and permissions.
    """

    id: int | str
    email: str
    name: str
    password_hash: str | None = None
    is_active: bool = True
    is_superuser: bool = False

    roles: list[str] = field(default_factory=list)
    permissions: set[str] = field(default_factory=set)

    # Metadata
    created_at: str | None = None
    last_login: str | None = None

    # Reference to framework auth user (set when delegated auth is active)
    framework_user: AuthenticatedUserProtocol | None = None

    @property
    def user_id(self) -> str:
        """Unique user identifier."""
        if self.framework_user is not None:
            return self.framework_user.user_id
        return str(self.id)

    @property
    def username(self) -> str:
        """Username of the authenticated user."""
        if self.framework_user is not None:
            return getattr(self.framework_user, "username", self.framework_user.name)
        return self.name

    @property
    def is_verified(self) -> bool:
        """Whether user is verified."""
        if self.framework_user is not None:
            return getattr(self.framework_user, "is_verified", self.is_active)
        return self.is_active

    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        if self.framework_user is not None:
            return getattr(self.framework_user, "is_authenticated", self.is_active)
        return self.is_active

    @property
    def is_admin(self) -> bool:
        """Check if user is admin."""
        if self.framework_user is not None:
            return (
                getattr(self.framework_user, "is_admin", False) or "admin" in self.roles
            )
        return self.is_superuser or "admin" in self.roles

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        if self.framework_user is not None and hasattr(self.framework_user, "has_role"):
            return self.framework_user.has_role(role)
        return role in self.roles or self.is_superuser

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        if self.framework_user is not None and hasattr(
            self.framework_user, "has_permission"
        ):
            return self.framework_user.has_permission(permission)
        if self.is_superuser:
            return True
        if permission in self.permissions:
            return True
        parts = permission.split(":")
        for i in range(len(parts)):
            wildcard = ":".join(parts[: i + 1]) + ":*"
            if wildcard in self.permissions:
                return True
        return False

    def has_any_permission(self, permissions: list[str]) -> bool:
        """Check if user has any of the given permissions."""
        return any(self.has_permission(p) for p in permissions)

    def has_all_permissions(self, permissions: list[str]) -> bool:
        """Check if user has all of the given permissions."""
        return all(self.has_permission(p) for p in permissions)


__all__ = [
    "AdminUser",
    "AuthenticatedUserProtocol",
    "PasswordHasherProtocol",
]
