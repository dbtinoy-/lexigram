"""Auth password and provider protocol class definitions."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from lexigram.contracts.core.provider import ProviderProtocol


@runtime_checkable
class LoginAttemptTrackerProtocol(Protocol):
    """Protocol for tracking failed login attempts and enforcing account lockout.

    Implementations must handle both in-process and distributed state (e.g.
    backed by a cache) so that multiple application instances share a
    consistent view of the failure window.
    """

    async def is_locked(self, identifier: str) -> bool:
        """Return ``True`` if *identifier* has exceeded the failure threshold.

        Args:
            identifier: Username, e-mail address, or IP used as the tracking key.

        Returns:
            ``True`` when the account is currently locked out, ``False`` otherwise.
        """
        ...

    async def record_failure(self, identifier: str) -> None:
        """Record a failed authentication attempt for *identifier*.

        Args:
            identifier: Username, e-mail address, or IP used as the tracking key.
        """
        ...

    async def clear(self, identifier: str) -> None:
        """Remove all recorded failures for *identifier* (call on successful login).

        Args:
            identifier: Username, e-mail address, or IP used as the tracking key.
        """
        ...


@runtime_checkable
class PasswordHasherProtocol(Protocol):
    """Protocol for password hashing services.

    Responsible for hashing passwords and verifying them against hashes.
    """

    async def hash(self, password: str) -> str:
        """Hash a plain text password.

        Args:
            password: Plain text password.

        Returns:
            Hashed password string.
        """
        ...

    async def verify(self, password: str, hashed_password: str) -> bool:
        """Verify a password against a hash.

        Args:
            password: Plain text password to check.
            hashed_password: Stored hash to compare against.

        Returns:
            True if password matches hash, False otherwise.
        """
        ...


@runtime_checkable
class PasswordPolicyProtocol(Protocol):
    """Protocol for password policy enforcement.

    Validates that a plain-text password satisfies the application's
    complexity requirements (minimum length, character classes, etc.).
    """

    def validate(self, password: str) -> None:
        """Validate password against the policy.

        Args:
            password: Plain text password to validate.

        Raises:
            ValidationError: If the password violates the policy.
        """
        ...

    def is_valid(self, password: str) -> bool:
        """Return True if the password satisfies the policy without raising.

        Args:
            password: Plain text password.

        Returns:
            True if valid, False otherwise.
        """
        ...


@runtime_checkable
class MFAManagerProtocol(Protocol):
    """Protocol for multi-factor authentication lifecycle management."""

    async def enroll(self, user_id: str, method: str) -> dict[str, Any]: ...
    async def verify(self, user_id: str, method: str, code: str) -> bool: ...
    async def revoke(self, user_id: str, method: str) -> None: ...
    async def list_methods(self, user_id: str) -> list[str]: ...
    async def get_mfa(self, user_id: str) -> Any | None: ...


@runtime_checkable
class AuthProviderProtocol(ProviderProtocol, Protocol):
    """Protocol for authentication and authorization providers.

    Auth providers are responsible for user authentication, authorization,
    token management, and access control.
    """

    # Optional managers — None when the feature is disabled/not configured
    user_store: Any | None
    session_manager: Any | None
    delegation_manager: Any | None
    api_key_manager: Any | None
    mfa_manager: MFAManagerProtocol | None

    async def get_user(self, user_id: str) -> Any | None:
        """Retrieve a user by their unique identifier.

        Args:
            user_id: Unique user identifier.

        Returns:
            User object or None if not found.
        """
        ...

    async def verify_token(self, token: str) -> Any:
        """Verify an encoded auth token and return verification details.

        Args:
            token: Raw encoded auth token (JWT or similar).

        Returns:
            Verification result (typically ``Result[VerifiedToken, TokenError]``).
        """
        ...

    def has_any_role(self, user: Any, roles: list[str]) -> bool:
        """Return True if *user* holds at least one of the given roles.

        Args:
            user: Authenticated user object.
            roles: Role names to check.

        Returns:
            True if the user has at least one of the supplied roles.
        """
        ...

    def has_any_permission(self, user: Any, permissions: list[str]) -> bool:
        """Return True if *user* has at least one of the given permissions.

        Args:
            user: Authenticated user object.
            permissions: Permission names to check.

        Returns:
            True if the user has at least one of the supplied permissions.
        """
        ...


__all__ = [
    "AuthProviderProtocol",
    "LoginAttemptTrackerProtocol",
    "MFAManagerProtocol",
    "PasswordHasherProtocol",
    "PasswordPolicyProtocol",
]
