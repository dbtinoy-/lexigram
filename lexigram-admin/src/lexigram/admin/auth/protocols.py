"""Admin authentication service protocols.

All protocols remain in lexigram-admin (not lexigram-contracts) because they
are admin-specific and not consumed by other extension packages.

``AdminAuditLogServiceProtocol`` extends the framework-wide
``AuditLoggerProtocol`` from ``lexigram.contracts.audit`` so that admin audit
implementations satisfy the cross-package contract.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from lexigram.contracts.audit import AuditLoggerProtocol

if TYPE_CHECKING:
    from datetime import datetime

    from lexigram.admin.auth.errors import AdminAuthError
    from lexigram.admin.auth.types import (
        AdminAuthResult,
        AdminLockoutInfo,
        AdminLoginAttempt,
        AdminPasswordResetToken,
        AdminPasswordValidationResult,
        AdminSecurityEvent,
        AdminSecurityEventType,
    )
    from lexigram.result import Result


@runtime_checkable
class AdminAuthServiceProtocol(Protocol):
    """Main authentication orchestration service protocol.

    Coordinates credential verification, rate limiting, lockout checks,
    session issuance, and audit logging.
    """

    async def authenticate(
        self,
        email: str,
        password: str,
        ip_address: str,
        user_agent: str,
    ) -> Result[AdminAuthResult, AdminAuthError]:
        """Authenticate an admin user with full security pipeline.

        Args:
            email: Admin user email.
            password: Plain-text password.
            ip_address: Client IP for rate limiting.
            user_agent: Client user agent for audit.

        Returns:
            Ok(AdminAuthResult) with session details on success.
            Err with specific AdminAuthError subclass on failure.
        """
        ...

    async def invalidate_session(self, session_id: str) -> None:
        """Invalidate a session (logout).

        Args:
            session_id: Session identifier to revoke.
        """
        ...

    async def invalidate_all_user_sessions(self, user_id: str) -> None:
        """Revoke all active sessions for a user (e.g., after password change).

        Args:
            user_id: Admin user UUID whose sessions to revoke.
        """
        ...

    async def complete_mfa_login(
        self,
        user_id: str,
        email: str,
        roles: list[str],
        code: str,
        ip_address: str,
        user_agent: str,
    ) -> Result[AdminAuthResult, AdminAuthError]:
        """Complete a login after a successful TOTP challenge.

        Verifies the code, then runs the post-credential pipeline
        (attempt recording, lockout clearance, session creation, audits)
        that was deferred when ``authenticate`` returned ``mfa_required``.

        Args:
            user_id: Admin user UUID (from the pending challenge).
            email: Admin user email (from the pending challenge).
            roles: Role names for the user (from the pending challenge).
            code: TOTP code to verify.
            ip_address: Client IP for rate limiting.
            user_agent: Client user agent for audit.

        Returns:
            Ok(AdminAuthResult) with a real session on success.
            Err(MfaVerificationFailedError) when the code is invalid.
            Err(MfaNotEnabledError) when 2FA is unavailable.
        """
        ...


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


@runtime_checkable
class AdminAuditLogStoreProtocol(Protocol):
    """Persistence protocol for security audit log entries."""

    async def ensure_schema(self) -> None:
        """Create the admin_security_audit_log table if it does not exist."""
        ...

    async def insert(self, event: AdminSecurityEvent) -> None:
        """Persist a security event.

        Args:
            event: Security event to store.
        """
        ...

    async def query_recent(
        self,
        admin_user_id: str | None = None,
        event_type: AdminSecurityEventType | None = None,
        since_seconds: int = 3600,
        limit: int = 100,
    ) -> list[AdminSecurityEvent]:
        """Query recent security events with optional filters.

        Args:
            admin_user_id: Filter to specific user (None = all users).
            event_type: Filter to specific event type (None = all types).
            since_seconds: Look-back window in seconds.
            limit: Maximum records to return.

        Returns:
            List of matching security events, newest first.
        """
        ...


@runtime_checkable
class AdminAuditLogServiceProtocol(AuditLoggerProtocol, Protocol):
    """Service for recording admin security events.

    Extends the framework-wide ``AuditLoggerProtocol`` so that admin audit
    implementations satisfy the cross-package contract. Adds admin-specific
    methods (``log_event``, ``get_recent_events``) on top of the base
    ``log()`` and ``query()`` methods from ``AuditLoggerProtocol``.

    Implementations must never raise — audit failures are swallowed so that
    an audit store outage cannot interrupt authentication flows.
    """

    async def log_event(
        self,
        event_type: AdminSecurityEventType,
        ip_address: str,
        user_agent: str,
        success: bool,
        admin_user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a security event. Implementation must never raise.

        Args:
            event_type: Type of security event.
            ip_address: Client IP.
            user_agent: Client user agent.
            success: Whether the operation succeeded.
            admin_user_id: Associated admin user (None for pre-auth events).
            metadata: Optional structured context.
        """
        ...

    async def get_recent_events(
        self,
        admin_user_id: str | None = None,
        since_seconds: int = 3600,
        limit: int = 50,
    ) -> list[AdminSecurityEvent]:
        """Retrieve recent security events for display.

        Args:
            admin_user_id: Filter to specific user.
            since_seconds: Look-back window.
            limit: Maximum results.

        Returns:
            List of security events, newest first.
        """
        ...


@runtime_checkable
class AdminPasswordPolicyServiceProtocol(Protocol):
    """Password policy validation service."""

    def validate(
        self,
        password: str,
        email: str | None = None,
    ) -> AdminPasswordValidationResult:
        """Validate a password against all configured policy rules.

        Returns ALL violations, not just the first one.

        Args:
            password: Plain-text password to validate.
            email: Optional email — used to check if password contains it.

        Returns:
            AdminPasswordValidationResult with is_valid and full violations list.
        """
        ...


@runtime_checkable
class AdminCsrfServiceProtocol(Protocol):
    """CSRF token generation and validation service."""

    def generate_token(self, session_id: str) -> str:
        """Generate a CSRF token scoped to the given session.

        Token format: base64url(timestamp:nonce:hmac_signature)

        Args:
            session_id: Session ID to scope the token to.

        Returns:
            CSRF token string.
        """
        ...

    def validate_token(self, session_id: str, token: str) -> bool:
        """Validate a CSRF token against the session.

        Uses hmac.compare_digest for timing-safe comparison.

        Args:
            session_id: Session ID the token was generated for.
            token: Token to validate.

        Returns:
            True if valid and not expired, False otherwise.
        """
        ...


@runtime_checkable
class AdminSessionServiceProtocol(Protocol):
    """Admin session lifecycle management service."""

    async def create_session(
        self,
        user_id: str,
        email: str,
        roles: list[str],
        ip_address: str,
        user_agent: str,
    ) -> str:
        """Create a new session and return the session ID.

        Args:
            user_id: Admin user UUID.
            email: Admin user email.
            roles: User's roles.
            ip_address: Client IP.
            user_agent: Client user agent.

        Returns:
            New session identifier (secrets.token_urlsafe(32)).
        """
        ...

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve session data if valid (not expired, not revoked).

        Checks both idle timeout and absolute expiry.

        Args:
            session_id: Session to retrieve.

        Returns:
            Session data dict or None if not found/expired.
        """
        ...

    async def touch_session(self, session_id: str) -> None:
        """Update session last-active timestamp.

        Args:
            session_id: Session to touch.
        """
        ...

    async def revoke_session(self, session_id: str) -> None:
        """Revoke a single session.

        Args:
            session_id: Session to revoke.
        """
        ...

    async def revoke_all_user_sessions(self, user_id: str) -> None:
        """Revoke all sessions for a user.

        Args:
            user_id: Admin user UUID.
        """
        ...


@runtime_checkable
class AdminPasswordResetTokenStoreProtocol(Protocol):
    """Persistence contract for password reset tokens.

    Implementations:
        - :class:`~lexigram.admin.auth.store.password_reset_token_sql.AdminPasswordResetTokenSqlStore`
    """

    async def ensure_schema(self) -> None:
        """Create the token table if it does not exist."""
        ...

    async def create(self, email: str, token_hash: str, expires_at: datetime) -> None:
        """Persist a new token record.

        Args:
            email: Email the token is issued for.
            token_hash: sha256 hex digest of the raw token.
            expires_at: UTC expiry timestamp.
        """
        ...

    async def find_by_hash(self, token_hash: str) -> AdminPasswordResetToken | None:
        """Look up a token by its sha256 hash.

        Args:
            token_hash: sha256 hex digest of the raw token.

        Returns:
            Token record or ``None`` when unknown.
        """
        ...

    async def mark_consumed(self, token_hash: str) -> bool:
        """Atomically verify-and-consume a token in one statement.

        Args:
            token_hash: sha256 hex digest of the raw token.

        Returns:
            ``True`` only when the token existed, was unconsumed, and had
            not expired at the instant of the write; ``False`` otherwise
            — the caller cannot distinguish missing, already-consumed,
            or expired without a separate lookup.
        """
        ...


@runtime_checkable
class AdminMfaStoreProtocol(Protocol):
    """Persistence contract for per-user TOTP secrets.

    Implementations:
        - :class:`~lexigram.admin.auth.store.mfa_sql.AdminMfaSqlStore`
    """

    async def ensure_schema(self) -> None:
        """Create the MFA table if it does not exist."""
        ...

    async def is_enabled(self, user_id: str) -> bool:
        """Return True when 2FA is enabled for the user."""
        ...

    async def get_secret(self, user_id: str) -> str | None:
        """Return the stored TOTP secret (None when disabled)."""
        ...

    async def save_secret(self, user_id: str, secret: str) -> None:
        """Persist (or refresh) the TOTP secret for a user."""
        ...

    async def disable(self, user_id: str) -> None:
        """Remove the TOTP secret (2FA off)."""
        ...


@runtime_checkable
class AdminMfaServiceProtocol(Protocol):
    """TOTP 2FA orchestration contract.

    Implementations:
        - :class:`~lexigram.admin.auth.services.mfa_service.AdminMfaService`
    """

    async def is_enabled(self, user_id: str) -> bool:
        """Return True when 2FA is enabled for the user."""
        ...

    async def start_setup(
        self, user_id: str, email: str
    ) -> Result[tuple[str, str, str], AdminAuthError]:
        """Generate a TOTP secret, provisioning URI, and QR SVG (no persist).

        Returns:
            ``Ok((secret, otpauth_uri, svg))`` on success; ``Err`` when 2FA
            is disabled in configuration.
        """
        ...

    async def confirm_setup(
        self, user_id: str, secret: str, code: str
    ) -> Result[None, AdminAuthError]:
        """Validate a code against a new secret and persist it."""
        ...

    async def verify_code(
        self, user_id: str, code: str
    ) -> Result[bool, AdminAuthError]:
        """Validate a TOTP code; ``Err`` when 2FA is not enabled."""
        ...

    async def disable(self, user_id: str, code: str) -> Result[bool, AdminAuthError]:
        """Disable 2FA (requires a valid current code)."""
        ...

    def get_factor(self) -> str:
        """Return the configured second factor (``"totp"`` or ``"email"``)."""
        ...


@runtime_checkable
class AdminEmailVerificationStoreProtocol(Protocol):
    """Persistence contract for admin email verification state.

    Implementations:
        - :class:`~lexigram.admin.auth.store.email_verification_sql.AdminEmailVerificationSqlStore`
    """

    async def ensure_schema(self) -> None:
        """Create the verification table if it does not exist."""
        ...

    async def is_verified(self, user_id: str) -> bool:
        """Return True when the user's email is verified.

        Args:
            user_id: Admin user UUID.
        """
        ...

    async def find_user_by_token_hash(self, token_hash: str) -> str | None:
        """Look up the user owning an unconsumed token.

        Args:
            token_hash: sha256 hex digest of the raw token.

        Returns:
            User UUID or ``None`` when no unconsumed token matches.
        """
        ...

    async def save_token(
        self, user_id: str, token_hash: str, expires_at: datetime
    ) -> None:
        """Persist (or refresh) the verification token for a user.

        Args:
            user_id: Admin user UUID.
            token_hash: sha256 hex digest of the raw token.
            expires_at: UTC expiry timestamp.
        """
        ...

    async def consume_token(self, user_id: str, token_hash: str) -> bool:
        """Atomically verify + consume a token.

        Marks the email verified and clears the token when the hash matches,
        the token is unexpired, and the email is not already verified.

        Args:
            user_id: Admin user UUID.
            token_hash: sha256 hex digest of the raw token.

        Returns:
            ``True`` when the token was valid and consumed.
        """
        ...

    async def clear_token(self, user_id: str) -> None:
        """Remove the pending verification token for a user.

        Args:
            user_id: Admin user UUID.
        """
        ...


@runtime_checkable
class AdminEmailOtpStoreProtocol(Protocol):
    """Persistence contract for email one-time-password codes.

    Implementations:
        - :class:`~lexigram.admin.auth.store.email_otp_sql.AdminEmailOtpSqlStore`
    """

    async def ensure_schema(self) -> None:
        """Create the OTP table if it does not exist."""
        ...

    async def save(self, user_id: str, code_hash: str, expires_at: datetime) -> None:
        """Persist a new emailed code.

        Args:
            user_id: Admin user UUID.
            code_hash: sha256 hex digest of the raw code.
            expires_at: UTC expiry timestamp.
        """
        ...

    async def consume(self, user_id: str, code_hash: str) -> bool:
        """Atomically consume a matching unexpired code.

        Args:
            user_id: Admin user UUID.
            code_hash: sha256 hex digest of the raw code.

        Returns:
            ``True`` when an unexpired, unused code matched and was consumed.
        """
        ...

    async def last_sent_at(self, user_id: str) -> datetime | None:
        """Return the creation time of the most recent code.

        Args:
            user_id: Admin user UUID.

        Returns:
            UTC datetime of the newest code, or ``None`` when none exists.
        """
        ...


@runtime_checkable
class AdminEmailOtpServiceProtocol(Protocol):
    """Email one-time-password factor contract.

    Implementations:
        - :class:`~lexigram.admin.auth.services.email_otp_service.AdminEmailOtpService`
    """

    async def send_otp(
        self, user_id: str, email: str, user_name: str
    ) -> Result[None, AdminAuthError]:
        """Generate, persist, and email a fresh one-time code.

        Returns:
            ``Ok(None)`` on success; ``Err`` when disabled, in cooldown, or
            undeliverable.
        """
        ...

    async def verify_otp(self, user_id: str, code: str) -> Result[bool, AdminAuthError]:
        """Verify a code and consume it when valid.

        Returns:
            ``Ok(True)`` on match; ``Ok(False)`` otherwise;
            ``Err`` when the factor is disabled.
        """
        ...


@runtime_checkable
class AdminEmailVerificationServiceProtocol(Protocol):
    """Email verification orchestration contract.

    Implementations:
        - :class:`~lexigram.admin.auth.services.email_verification_service.AdminEmailVerificationService`
    """

    async def is_verified(self, user_id: str) -> bool:
        """Return True when the user's email is verified."""
        ...

    async def is_required(self, user_id: str) -> bool:
        """Return True when login must be gated on email verification."""
        ...

    async def send_verification(
        self,
        user_id: str,
        email: str,
        user_name: str,
        base_url: str = "",
        ip_address: str = "",
    ) -> Result[None, AdminAuthError]:
        """Issue a verification link and email it to the user.

        No-op (Ok) when disabled or already verified; fail-open on delivery.
        Rate limited per IP when a cache backend is wired (fail open).
        """
        ...

    async def verify_token(self, token: str) -> Result[bool, AdminAuthError]:
        """Validate and consume a verification token.

        Returns:
            ``Ok(True)`` on success; ``Err(EmailVerificationTokenInvalidError)``
            for unknown/used/expired tokens.
        """
        ...

    async def resend_verification(
        self,
        user_id: str,
        email: str,
        user_name: str,
        base_url: str = "",
        ip_address: str = "",
    ) -> Result[None, AdminAuthError]:
        """Re-issue and re-send the verification email."""
        ...


@runtime_checkable
class AdminPasswordResetServiceProtocol(Protocol):
    """Password reset orchestration contract."""

    async def request_reset(
        self,
        email: str,
        ip_address: str,
        user_agent: str,
        base_url: str,
    ) -> Result[None, AdminAuthError]:
        """Issue a reset token and notify the user.

        Always returns ``Ok(None)`` for unknown emails (anti-enumeration).
        """
        ...

    async def confirm_reset(
        self,
        token: str,
        new_password: str,
        ip_address: str = "",
        user_agent: str = "",
    ) -> Result[None, AdminAuthError]:
        """Validate a token and apply a new password.

        Consumes the token on success and invalidates all user sessions.
        """
        ...


__all__ = [
    "AdminAccountLockoutStoreProtocol",
    "AdminAuditLogServiceProtocol",
    "AdminAuditLogStoreProtocol",
    "AdminAuthServiceProtocol",
    "AdminCsrfServiceProtocol",
    "AdminEmailOtpServiceProtocol",
    "AdminEmailOtpStoreProtocol",
    "AdminEmailVerificationServiceProtocol",
    "AdminEmailVerificationStoreProtocol",
    "AdminLoginAttemptServiceProtocol",
    "AdminLoginAttemptStoreProtocol",
    "AdminMfaServiceProtocol",
    "AdminMfaStoreProtocol",
    "AdminPasswordPolicyServiceProtocol",
    "AdminPasswordResetServiceProtocol",
    "AdminPasswordResetTokenStoreProtocol",
    "AdminSessionServiceProtocol",
]
