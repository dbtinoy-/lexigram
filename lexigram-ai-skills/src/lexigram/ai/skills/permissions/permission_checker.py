"""PermissionChecker — verifies a user has the required permissions to run a skill."""

from __future__ import annotations

from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class PermissionChecker:
    """Grant and verify per-user permission sets for skill execution.

    Permissions are plain strings (e.g. ``"files.read"``, ``"db.query"``).
    A user with no registered permissions is treated as having *no* permissions.

    Example::

        checker = PermissionChecker()
        checker.grant("user-123", {"files.read", "web.search"})
        allowed = checker.check("user-123", {"files.read"})   # True
        denied  = checker.check("user-123", {"db.write"})     # False
    """

    def __init__(self) -> None:
        """Initialise an empty permission store."""
        self._permissions: dict[str, set[str]] = {}

    def grant(self, user_id: str, permissions: set[str]) -> None:
        """Add permissions for a user.

        Args:
            user_id: The user identifier.
            permissions: Set of permission strings to grant.
        """
        if user_id not in self._permissions:
            self._permissions[user_id] = set()
        self._permissions[user_id].update(permissions)
        logger.debug("permissions_granted", user_id=user_id, count=len(permissions))

    def revoke(self, user_id: str, permissions: set[str]) -> None:
        """Remove permissions for a user.

        Args:
            user_id: The user identifier.
            permissions: Set of permission strings to revoke.
        """
        if user_id in self._permissions:
            self._permissions[user_id].difference_update(permissions)

    def set_permissions(self, user_id: str, permissions: set[str]) -> None:
        """Replace all permissions for a user with the given set.

        Args:
            user_id: The user identifier.
            permissions: Complete replacement permission set.
        """
        self._permissions[user_id] = set(permissions)

    def get_permissions(self, user_id: str) -> set[str]:
        """Return the current permission set for a user.

        Args:
            user_id: The user identifier.

        Returns:
            Set of permission strings (may be empty).
        """
        return set(self._permissions.get(user_id, set()))

    def check(self, user_id: str, required: set[str]) -> bool:
        """Check whether a user possesses *all* required permissions.

        Args:
            user_id: The user to check.
            required: Permissions that must all be present.

        Returns:
            ``True`` if every required permission is granted; ``False``
            otherwise (including when *required* is empty — returns ``True``).
        """
        if not required:
            return True
        user_perms = self._permissions.get(user_id, set())
        allowed = required.issubset(user_perms)
        if not allowed:
            missing = required - user_perms
            logger.debug(
                "permission_check_denied",
                user_id=user_id,
                missing=sorted(missing),
            )
        return allowed
