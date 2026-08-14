"""Admin module user record.

Provides a lightweight user dataclass for the admin subsystem that satisfies
the :class:`lexigram.contracts.auth.AuthenticatedUserProtocol` protocol without
importing from ``lexigram-auth``.

Cross-extension communication uses contracts only; the concrete ``User``
from ``lexigram-auth`` must not be imported here.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AdminUserRecord:
    """User record for the admin module.

    A plain dataclass that satisfies the ``AuthenticatedUserProtocol`` protocol from
    ``lexigram.contracts.auth``.  Instances are constructed locally within
    ``lexigram-admin`` (e.g. from ``AdminUserEntity.to_user()`` or from
    config-backed in-memory stores) and must never be imported from
    ``lexigram-auth``.
    """

    user_id: str
    email: str
    name: str = ""
    hashed_password: str | None = None
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    is_active: bool = True
    is_verified: bool = True

    def has_role(self, role: str) -> bool:
        """Return True if the user has the given role.

        Args:
            role: Role name to check.

        Returns:
            True when the role is present in :attr:`roles`.
        """
        return role in self.roles

    def has_permission(self, permission: str) -> bool:
        """Return True if the user has the given permission.

        Args:
            permission: Permission name to check.

        Returns:
            True when the permission is present in :attr:`permissions`.
        """
        return permission in self.permissions


__all__ = ["AdminUserRecord"]
