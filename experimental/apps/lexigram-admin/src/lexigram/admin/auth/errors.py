"""Admin authentication exceptions.

Leaf exception hierarchy for admin auth. All exceptions are intentionally
minimal — descriptive docstrings and a standard message only, no extra logic.

``AdminAuthError`` extends ``DomainError`` because admin auth failures are
expected, recoverable domain failures (invalid credentials, locked accounts,
expired sessions) rather than infrastructure or programming errors.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from lexigram.contracts.exceptions.domain import DomainError


class AdminAuthError(DomainError):
    """Base exception for all admin authentication errors."""

    _code: str = "LEX_ERR_ADMIN_010"


class InvalidCredentialsError(AdminAuthError):
    """Raised when email/password combination is incorrect."""

    _code: str = "LEX_ERR_ADMIN_011"


class AccountLockedError(AdminAuthError):
    """Raised when an account is temporarily or permanently locked.

    Args:
        message: Human-readable description.
        unlock_at: When the lock expires (None for permanent lockout).
        retry_after: Seconds until retry is permitted.
        reason: Categorised reason string (lockout, rate_limit, etc.).
    """

    _code: str = "LEX_ERR_ADMIN_012"

    def __init__(
        self,
        message: str,
        unlock_at: datetime | None = None,
        retry_after: int | None = None,
        reason: str = "lockout",
    ) -> None:
        super().__init__(message)
        self.unlock_at = unlock_at
        self.retry_after = retry_after
        self.reason = reason

    def to_payload(self) -> dict[str, Any]:
        """Return a structured error payload for API responses.

        Returns:
            Dict with reason, unlock_at (ISO8601), and retry_after keys.
        """
        payload: dict[str, Any] = {"reason": self.reason}
        if self.unlock_at is not None:
            payload["unlock_at"] = self.unlock_at.isoformat()
        if self.retry_after is not None:
            payload["retry_after"] = self.retry_after
        return payload


class RateLimitExceededError(AdminAuthError):
    """Raised when the IP-based rate limit is exceeded.

    Args:
        message: Human-readable description.
        retry_after: Seconds until retry is permitted.
        reason: Categorised reason string.
    """

    _code: str = "LEX_ERR_ADMIN_013"

    def __init__(
        self,
        message: str,
        retry_after: int | None = None,
        reason: str = "rate_limit",
    ) -> None:
        super().__init__(message)
        self.retry_after = retry_after
        self.reason = reason

    def to_payload(self) -> dict[str, Any]:
        """Return a structured error payload for API responses.

        Returns:
            Dict with reason and retry_after keys.
        """
        payload: dict[str, Any] = {"reason": self.reason}
        if self.retry_after is not None:
            payload["retry_after"] = self.retry_after
        return payload


class SessionNotFoundError(AdminAuthError):
    """Raised when the requested session does not exist."""

    _code: str = "LEX_ERR_ADMIN_014"


class SessionExpiredError(AdminAuthError):
    """Raised when the session has exceeded its idle or absolute timeout."""

    _code: str = "LEX_ERR_ADMIN_015"


class CsrfValidationError(AdminAuthError):
    """Raised when CSRF token is missing, invalid, or expired."""

    _code: str = "LEX_ERR_ADMIN_016"


class PasswordPolicyError(AdminAuthError):
    """Raised when a password does not meet policy requirements."""

    _code: str = "LEX_ERR_ADMIN_017"


class SetupAlreadyCompletedError(AdminAuthError):
    """Raised when setup is attempted after an admin account already exists."""

    _code: str = "LEX_ERR_ADMIN_018"


class SetupTokenInvalidError(AdminAuthError):
    """Raised when the ADMIN_SETUP_TOKEN env var is set and the provided token doesn't match."""

    _code: str = "LEX_ERR_ADMIN_019"


class PasswordResetTokenInvalidError(AdminAuthError):
    """Raised when a password reset token is unknown or already consumed."""

    _code: str = "LEX_ERR_ADMIN_020"


class PasswordResetTokenExpiredError(AdminAuthError):
    """Raised when a password reset token has expired."""

    _code: str = "LEX_ERR_ADMIN_021"


class MfaNotEnabledError(AdminAuthError):
    """Raised when 2FA is required but not configured/enabled."""

    _code: str = "LEX_ERR_ADMIN_022"


class MfaVerificationFailedError(AdminAuthError):
    """Raised when a TOTP code is missing, invalid, or expired."""

    _code: str = "LEX_ERR_ADMIN_023"


class EmailVerificationRequiredError(AdminAuthError):
    """Raised when login is blocked because the email is unverified."""

    _code: str = "LEX_ERR_ADMIN_024"


class EmailVerificationTokenInvalidError(AdminAuthError):
    """Raised when a verification token is missing, invalid, used, or expired."""

    _code: str = "LEX_ERR_ADMIN_025"


class EmailOtpDeliveryError(AdminAuthError):
    """Raised when an email OTP cannot be delivered."""

    _code: str = "LEX_ERR_ADMIN_026"


class EmailOtpCooldownError(AdminAuthError):
    """Raised when an email OTP resend is attempted too soon."""

    _code: str = "LEX_ERR_ADMIN_027"


__all__ = [
    "AccountLockedError",
    "AdminAuthError",
    "CsrfValidationError",
    "EmailOtpCooldownError",
    "EmailOtpDeliveryError",
    "EmailVerificationRequiredError",
    "EmailVerificationTokenInvalidError",
    "InvalidCredentialsError",
    "MfaNotEnabledError",
    "MfaVerificationFailedError",
    "PasswordPolicyError",
    "PasswordResetTokenExpiredError",
    "PasswordResetTokenInvalidError",
    "RateLimitExceededError",
    "SessionExpiredError",
    "SessionNotFoundError",
    "SetupAlreadyCompletedError",
    "SetupTokenInvalidError",
]
