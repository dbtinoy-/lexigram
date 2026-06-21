"""Password reset orchestration service for the admin panel.

Coordinates the full reset flow: token issuance, hashed-token persistence,
email notification (optional), password policy validation, password update,
token consumption, session invalidation, and audit logging.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import secrets

from lexigram.admin.auth.errors import (
    AdminAuthError,
    PasswordPolicyError,
    PasswordResetTokenExpiredError,
    PasswordResetTokenInvalidError,
    RateLimitExceededError,
)
from lexigram.admin.auth.protocols import (
    AdminAuditLogServiceProtocol,
    AdminAuthServiceProtocol,
    AdminPasswordPolicyServiceProtocol,
    AdminPasswordResetTokenStoreProtocol,
)
from lexigram.admin.auth.store.protocols import AdminUserStoreProtocol
from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.services.notifications import AdminNotificationService
from lexigram.contracts.auth import PasswordHasherProtocol
from lexigram.contracts.infra.cache import CacheBackendProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)


@inject
class AdminPasswordResetService:
    """Password reset orchestrator (see module docstring).

    Anti-enumeration: ``request_reset`` returns ``Ok(None)`` for unknown
    emails, producing an identical "check your email" response in all cases.

    Args:
        user_store: Admin user persistence (lookup + password update).
        token_store: Persistence for single-use reset tokens.
        audit_service: Security event recording (fire-and-forget).
        auth_service: Session invalidation after a successful reset.
        policy_service: New-password policy validation.
        hasher: Password hasher; defaults to ``PasswordHasher`` from
            ``lexigram-auth`` when ``None``.
        notification_service: Optional email notification; ``None`` skips
            sending.
        token_lifetime: Token validity in seconds (default 3600 = 1 hour).
        cache: Optional cache backend for request rate limiting; ``None`` (or
            a failing cache) skips limiting (fail open).
        reset_request_limit: Max request-reset calls per IP per window.
        reset_request_window_seconds: Rate-limit window length in seconds.
    """

    def __init__(
        self,
        user_store: AdminUserStoreProtocol,
        token_store: AdminPasswordResetTokenStoreProtocol,
        audit_service: AdminAuditLogServiceProtocol,
        auth_service: AdminAuthServiceProtocol,
        policy_service: AdminPasswordPolicyServiceProtocol,
        hasher: PasswordHasherProtocol | None = None,
        notification_service: AdminNotificationService | None = None,
        token_lifetime: int = 3600,
        cache: CacheBackendProtocol | None = None,
        reset_request_limit: int = 5,
        reset_request_window_seconds: int = 3600,
    ) -> None:
        self._user_store = user_store
        self._token_store = token_store
        self._audit_service = audit_service
        self._auth_service = auth_service
        self._policy_service = policy_service
        self._hasher = hasher
        self._notification_service = notification_service
        self._token_lifetime = token_lifetime
        self._cache = cache
        self._reset_request_limit = reset_request_limit
        self._reset_request_window_seconds = reset_request_window_seconds

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def request_reset(
        self,
        email: str,
        ip_address: str,
        user_agent: str,
        base_url: str,
    ) -> Result[None, AdminAuthError]:
        """Issue a reset token and notify the user.

        Always returns ``Ok(None)`` for unknown emails so the response is
        identical in all cases (anti-enumeration).  A token is persisted
        (sha256 of the raw token) only when the email matches an account;
        the audit event is also emitted only for real accounts.

        Args:
            email: Email to send the reset link to.
            ip_address: Client IP for audit and rate limiting.
            user_agent: Client user agent for audit.
            base_url: Request base URL used to build the reset link.

        Returns:
            ``Ok(None)`` — always, regardless of whether the email exists —
            or ``Err(RateLimitExceededError)`` when this IP exceeds the
            request limit.
        """
        email = email.strip().lower()

        if self._cache is not None and await self._is_rate_limited(ip_address):
            logger.warning("admin.password_reset_rate_limited", ip=ip_address)
            return Err(
                RateLimitExceededError(
                    "Too many password reset requests. Please try again later.",
                    reason="rate_limit",
                )
            )

        user = await self._user_store.get_user_by_email(email)
        if user is None:
            logger.info("admin.password_reset_unknown_email", email=email)
            return Ok(None)

        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.now(UTC) + timedelta(seconds=self._token_lifetime)
        await self._token_store.create(email, token_hash, expires_at)

        if self._notification_service is not None:
            reset_url = f"{base_url.rstrip('/')}/admin/password-reset/{raw_token}"
            result = await self._notification_service.notify_password_reset(
                user_email=email,
                user_name=getattr(user, "name", email),
                reset_url=reset_url,
                expires_in=f"{self._token_lifetime // 60} minutes",
            )
            if getattr(result, "is_err", lambda: False)():
                logger.warning(
                    "admin.password_reset_notify_failed",
                    email=email,
                    error=str(result.unwrap_err()),
                )

        await self._audit_service.log_event(
            event_type=AdminSecurityEventType.PASSWORD_RESET_REQUESTED,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
            admin_user_id=getattr(user, "user_id", None),
            metadata={"email": email},
        )
        logger.info("admin.password_reset_requested", email=email)
        return Ok(None)

    async def _is_rate_limited(self, ip_address: str) -> bool:
        """Check and increment the per-IP request counter. Fail open.

        Uses a fixed-window counter keyed by a sha256 hash of the client IP
        (avoids PII in cache key listings). Any cache failure is treated as
        "not limited" so a cache outage never blocks password resets.

        Args:
            ip_address: Client IP address.

        Returns:
            ``True`` when the IP exceeds ``reset_request_limit``.
        """
        try:
            ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()[:16]
            key = f"admin:password-reset:ip:{ip_hash}"
            cache = self._cache
            if cache is None:
                return False
            result = await cache.get(key)
            value = result.unwrap() if result.is_ok() else None
            count = int(value) if value else 0
            if count >= self._reset_request_limit:
                return True
            await cache.set(
                key, str(count + 1), ttl=self._reset_request_window_seconds
            )
            return False
        except Exception:  # noqa: BLE001
            logger.warning("admin.password_reset_rate_limit_unavailable")
            return False

    async def confirm_reset(
        self,
        token: str,
        new_password: str,
        ip_address: str = "",
        user_agent: str = "",
    ) -> Result[
        None,
        PasswordResetTokenInvalidError
        | PasswordResetTokenExpiredError
        | PasswordPolicyError,
    ]:
        """Validate a token and apply a new password.

        Consumes the token and revokes all active sessions for the user on
        success.

        Args:
            token: Raw reset token from the emailed link.
            new_password: New plain-text password (policy-validated).
            ip_address: Client IP for audit.
            user_agent: Client user agent for audit.

        Returns:
            ``Ok(None)`` on success, or an ``Err`` with a specific
            ``AdminAuthError`` subclass describing the failure.
        """
        token_hash = hashlib.sha256(token.strip().encode()).hexdigest()
        record = await self._token_store.find_by_hash(token_hash)
        if record is None or record.consumed_at is not None:
            return Err(PasswordResetTokenInvalidError())
        if record.expires_at < datetime.now(UTC):
            return Err(PasswordResetTokenExpiredError())

        validation = self._policy_service.validate(new_password, record.email)
        if not validation.is_valid:
            message = "; ".join(v.message for v in validation.violations)
            return Err(PasswordPolicyError(message))

        user = await self._user_store.get_user_by_email(record.email)
        if user is None:
            return Err(PasswordResetTokenInvalidError())

        hasher = self._hasher
        if hasher is None:
            from lexigram.auth.authn.security import PasswordHasher

            hasher = PasswordHasher()
        user.hashed_password = await hasher.hash(new_password)
        await self._user_store.update_user(user)
        await self._token_store.mark_consumed(token_hash)

        user_id = getattr(user, "user_id", None)
        if user_id:
            await self._auth_service.invalidate_all_user_sessions(user_id)

        await self._audit_service.log_event(
            event_type=AdminSecurityEventType.PASSWORD_CHANGED,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
            admin_user_id=user_id,
            metadata={"email": record.email},
        )
        logger.info("admin.password_reset_confirmed", email=record.email)
        return Ok(None)


__all__ = ["AdminPasswordResetService"]
