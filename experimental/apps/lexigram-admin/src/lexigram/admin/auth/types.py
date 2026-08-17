"""Admin authentication domain types and enumerations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AdminSecurityEventType(str, Enum):
    """Security audit event types tracked for admin authentication."""

    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGIN_BLOCKED_IP = "login_blocked_ip"
    LOGIN_BLOCKED_LOCKOUT = "login_blocked_lockout"
    LOGOUT = "logout"
    SESSION_CREATED = "session_created"
    SESSION_EXPIRED = "session_expired"
    SESSION_REVOKED = "session_revoked"
    SESSION_ROTATED = "session_rotated"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    PASSWORD_CHANGED = "password_changed"  # noqa: S105  # event type name, not a credential
    PASSWORD_RESET_REQUESTED = "password_reset_requested"  # noqa: S105  # event type name, not a credential
    SETUP_COMPLETED = "setup_completed"
    SETUP_BLOCKED = "setup_blocked"
    SETUP_TOKEN_USED = "setup_token_used"  # noqa: S105  # event type name, not a credential
    CSRF_VIOLATION = "csrf_violation"
    PERMISSION_DENIED = "permission_denied"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    ADMIN_UNLOCK = "admin_unlock"
    SETTINGS_UPDATED = "settings_updated"
    MFA_CHALLENGE_ISSUED = "mfa_challenge_issued"
    MFA_CHALLENGE_FAILED = "mfa_challenge_failed"
    MFA_VERIFIED = "mfa_verified"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    EMAIL_VERIFICATION_SENT = "email_verification_sent"
    EMAIL_VERIFIED = "email_verified"
    EMAIL_VERIFICATION_FAILED = "email_verification_failed"
    EMAIL_OTP_SENT = "email_otp_sent"
    EMAIL_OTP_FAILED = "email_otp_failed"
    ROLE_CREATED = "role_created"
    ROLE_UPDATED = "role_updated"
    ROLE_DELETED = "role_deleted"
    USER_REGISTERED = "user_registered"


class AdminLockoutStatus(str, Enum):
    """Account lockout status levels."""

    NONE = "none"
    SOFT = "soft"  # Delay added but not blocked
    LOCKED = "locked"  # Temporarily locked, auto-unlocks
    PERMANENT = "permanent"  # Requires manual admin unlock


class AdminPasswordRule(str, Enum):
    """Password policy rules that can be violated."""

    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"
    MISSING_UPPERCASE = "missing_uppercase"
    MISSING_LOWERCASE = "missing_lowercase"
    MISSING_DIGIT = "missing_digit"
    MISSING_SPECIAL = "missing_special"
    COMMON_PASSWORD = "common_password"  # noqa: S105  # policy rule name, not a credential
    CONTAINS_EMAIL = "contains_email"


@dataclass(frozen=True)
class AdminAuthResult:
    """Result of a successful authentication.

    Attributes:
        session_id: Newly created session identifier.
        user_id: Authenticated admin user's UUID.
        email: Authenticated admin user's email.
        roles: List of role names assigned to the user.
        expires_at: Absolute session expiry timestamp.
        mfa_required: True when the user must complete a 2FA challenge.
        email_verification_required: True when login is blocked until the
            email is verified.
    """

    session_id: str
    user_id: str
    email: str
    roles: list[str]
    expires_at: datetime
    mfa_required: bool = False
    email_verification_required: bool = False


@dataclass(frozen=True)
class AdminLockoutInfo:
    """Information about an account's lockout state.

    Attributes:
        status: Current lockout status.
        consecutive_failures: Total consecutive failed attempts.
        locked_at: When the lockout was applied (None if not locked).
        unlock_at: When the lockout will auto-expire (None if permanent/not locked).
        is_permanent: Whether the lockout requires manual admin intervention.
    """

    status: AdminLockoutStatus
    consecutive_failures: int
    locked_at: datetime | None = None
    unlock_at: datetime | None = None
    is_permanent: bool = False


@dataclass(frozen=True)
class AdminPasswordViolation:
    """A single password policy violation.

    Attributes:
        rule: The rule that was violated.
        message: Human-readable description of the violation.
    """

    rule: AdminPasswordRule
    message: str


@dataclass(frozen=True)
class AdminPasswordValidationResult:
    """Result of password policy validation.

    Attributes:
        is_valid: Whether the password passes all policy rules.
        violations: List of all violated rules (empty when valid).
    """

    is_valid: bool
    violations: list[AdminPasswordViolation] = field(default_factory=list)


@dataclass(frozen=True)
class AdminLoginAttempt:
    """Record of a single login attempt.

    Attributes:
        id: Unique UUID for this attempt record.
        email: Email address used in the attempt.
        ip_address: Client IP address.
        user_agent: Client user agent string.
        success: Whether the attempt succeeded.
        failure_reason: Short failure code (None on success).
        attempted_at: When the attempt occurred.
    """

    id: str
    email: str
    ip_address: str
    user_agent: str
    success: bool
    failure_reason: str | None
    attempted_at: datetime


@dataclass(frozen=True)
class AdminSecurityEvent:
    """A security audit event record.

    Attributes:
        id: Unique UUID for this event.
        event_type: Type of security event.
        admin_user_id: Associated admin user (None for pre-auth events).
        ip_address: Client IP address.
        user_agent: Client user agent string.
        success: Whether the operation succeeded.
        metadata: Structured additional context.
        created_at: When the event occurred.
    """

    id: str
    event_type: AdminSecurityEventType
    admin_user_id: str | None
    ip_address: str
    user_agent: str
    success: bool
    metadata: dict[str, str | int | bool | None]
    created_at: datetime


@dataclass(frozen=True)
class AdminPasswordResetToken:
    """Persisted password reset token record (sha256 of the raw token).

    Attributes:
        email: Email the reset token was issued for.
        token_hash: sha256 hex digest of the raw token — the raw token
            itself is never persisted.
        expires_at: UTC expiry timestamp.
        consumed_at: UTC consumption timestamp; ``None`` while unused.
    """

    email: str
    token_hash: str
    expires_at: datetime
    consumed_at: datetime | None = None


__all__ = [
    "AdminAuthResult",
    "AdminLockoutInfo",
    "AdminLockoutStatus",
    "AdminLoginAttempt",
    "AdminPasswordResetToken",
    "AdminPasswordRule",
    "AdminPasswordValidationResult",
    "AdminPasswordViolation",
    "AdminSecurityEvent",
    "AdminSecurityEventType",
]
