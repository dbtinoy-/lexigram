"""Admin user store protocol.

Defines the formal contract for admin panel user store implementations.
Any class that satisfies these method signatures is a valid implementation.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AdminUserStoreProtocol(Protocol):
    """Protocol for admin panel user store operations.

    This is the single authoritative contract for anything that stores and
    manages admin-panel user accounts (distinct from the application's own
    user store managed by lexigram-auth).

    Implementations:
        - :class:`~lexigram.admin.auth.store.direct_sql.DirectSQLAdminUserStore`
          — production SQL backend (``admin_users`` table)
        - :class:`~lexigram.admin.auth.store.memory.MemoryAdminUserStore`
          — in-memory store for testing
    """

    async def get_admin_count(self) -> int:
        """Return the total number of admin-panel accounts.

        Used by :class:`~lexigram.admin.middleware.setup.SetupMiddleware` to
        decide whether to redirect to the first-run setup wizard.

        Returns:
            Non-negative integer count of admin users.
        """
        ...

    async def ensure_schema(self) -> None:
        """Create the admin_users table if it does not exist (idempotent).

        Failures are logged and swallowed, never raised — matching the boot
        loop's swallow-and-log behavior.
        """
        ...

    async def list_users(self) -> list[Any]:
        """Return all admin users ordered by creation time."""
        ...

    async def create_user(
        self,
        name: str,
        email: str,
        hashed_password: str,
        roles: list[str] | None = None,
        permissions: list[str] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Create (or upsert) an admin-panel user account.

        Args:
            name: Display name.
            email: Unique email address — used as the login identifier.
            hashed_password: Pre-hashed credential.
            roles: Optional list of role strings (e.g. ``["superadmin"]``).
            permissions: Optional list of explicit permission strings.
            **kwargs: Implementation-specific extras (ignored if unsupported).

        Returns:
            A lightweight object exposing at least ``user_id``, ``name``, and
            ``email`` attributes.
        """
        ...

    async def get_user_by_email(self, email: str) -> Any | None:
        """Look up an admin user by email address.

        Args:
            email: Email to search for.

        Returns:
            User object or ``None`` when no match exists.
        """
        ...

    async def get_user_by_id(self, user_id: str) -> Any | None:
        """Look up an admin user by primary key.

        Args:
            user_id: Unique identifier (UUID string).

        Returns:
            User object or ``None`` when no match exists.
        """
        ...

    async def update_user(self, user: Any) -> None:
        """Persist changes to an existing admin user.

        Args:
            user: User object carrying updated field values.  Must expose at
                least ``user_id``, ``name``, ``email``, ``roles``,
                ``permissions``, ``hashed_password``, and ``is_active``.
        """
        ...

    async def delete_user(self, user_id: str) -> None:
        """Permanently remove an admin user account.

        Args:
            user_id: Unique identifier of the user to delete.
        """
        ...

    async def authenticate(self, email: str, password: str) -> Any | None:
        """Authenticate an admin user by email and password.

        Args:
            email: Email address to look up.
            password: Plain-text password to verify.

        Returns:
            User object when credentials are valid and account is active,
            ``None`` otherwise.
        """
        ...


__all__ = ["AdminUserStoreProtocol"]
