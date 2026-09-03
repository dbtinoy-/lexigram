"""Persistence protocols for login attempts and account lockouts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from lexigram.admin.auth.types import AdminLockoutInfo, AdminLoginAttempt


@runtime_checkable
class AdminLoginAttemptStoreProtocol(Protocol):
    """Persistence protocol for login attempt records."""

    async def ensure_schema(self) -> None:
        """Create the admin_login_attempts table if it does not exist."""
        ...

    async def insert(self, attempt: AdminLoginAttempt) -> None:
        """Persist a login attempt record.

        Args:
            attempt: The attempt to store.
        """
        ...

    async def count_recent_failures(self, email: str, since_seconds: int) -> int:
        """Count failed attempts for email within the given window.

        Args:
            email: Email address to query.
            since_seconds: Look-back window in seconds.

        Returns:
            Number of failed attempts.
        """
        ...

    async def count_recent_failures_by_ip(
        self, ip_address: str, since_seconds: int
    ) -> int:
        """Count failed attempts from an IP within the given window.

        Args:
            ip_address: IP address to query.
            since_seconds: Look-back window in seconds.

        Returns:
            Number of failed attempts.
        """
        ...

    async def clear_failures(self, email: str) -> None:
        """Clear failure records for email (called on successful login).

        Args:
            email: Email to clear.
        """
        ...


@runtime_checkable
class AdminAccountLockoutStoreProtocol(Protocol):
    """Persistence protocol for account lockout records."""

    async def ensure_schema(self) -> None:
        """Create the admin_account_lockouts table if it does not exist."""
        ...

    async def get_active_lockout(self, email: str) -> AdminLockoutInfo | None:
        """Get active lockout for email, or None if not locked.

        Args:
            email: Email to check.

        Returns:
            AdminLockoutInfo if active lockout exists, None otherwise.
        """
        ...

    async def create_lockout(
        self,
        email: str,
        consecutive_failures: int,
        unlock_at: Any | None,
        is_permanent: bool,
    ) -> None:
        """Create or update a lockout record for email.

        Args:
            email: Email to lock.
            consecutive_failures: Total consecutive failures.
            unlock_at: UTC datetime when lock expires (None if permanent).
            is_permanent: Whether this requires manual admin unlock.
        """
        ...

    async def clear_lockout(self, email: str) -> None:
        """Remove active lockout for email (on successful login or admin unlock).

        Args:
            email: Email to unlock.
        """
        ...
