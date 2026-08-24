"""Service protocol for IP rate limiting and account lockout enforcement."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class AdminLoginAttemptServiceProtocol(Protocol):
    """Service for IP rate limiting and account lockout enforcement."""

    async def check_ip_rate_limit(self, ip_address: str) -> None:
        """Check IP rate limit. Raises RateLimitExceededError if exceeded.

        Args:
            ip_address: Client IP to check.

        Raises:
            RateLimitExceededError: When the IP is rate-limited.
        """
        ...

    async def check_account_lockout(self, email: str) -> None:
        """Check account lockout status. Raises AccountLockedError if locked.

        Args:
            email: Email address to check.

        Raises:
            AccountLockedError: When the account is locked.
        """
        ...

    async def record_attempt(
        self,
        email: str,
        ip_address: str,
        user_agent: str,
        success: bool,
        failure_reason: str | None = None,
    ) -> None:
        """Record a login attempt and update lockout state on failure.

        Args:
            email: Email that attempted login.
            ip_address: Client IP.
            user_agent: Client user agent.
            success: Whether the attempt succeeded.
            failure_reason: Short failure code when success=False.
        """
        ...

    async def clear_lockout(self, email: str) -> None:
        """Clear lockout and failure records on successful login.

        Args:
            email: Email to clear.
        """
        ...
