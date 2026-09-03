"""Admin email verification orchestration service.

Handles the verify-your-email flow: issuing single-use verification links,
delivering them through the admin notification service, and consuming the
links.  Depends only on ``AdminEmailVerificationStoreProtocol`` from
``lexigram.admin.auth.protocols``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import secrets
from typing import TYPE_CHECKING

from lexigram.admin.auth.errors import (
    AdminAuthError,
    EmailVerificationTokenInvalidError,
    RateLimitExceededError,
)
from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.config import AdminEmailVerificationConfig
from lexigram.contracts.infra.cache import CacheBackendProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.admin.auth.protocols import (
        AdminAuditLogServiceProtocol,
        AdminEmailVerificationStoreProtocol,
    )
    from lexigram.admin.services.notifications import AdminNotificationService

logger = get_logger(__name__)


@inject
class AdminEmailVerificationService:
    """Email verification flow: links, delivery, and consumption.

    A verification link embeds a random token; the store keeps only its
    sha256 digest.  Delivery failures are surfaced: when no notification
    service (or mailer backend) is bound, sending fails with a descriptive
    error telling the operator which dependency to configure, so missing
    infrastructure is never silently swallowed.
    """

    def __init__(
        self,
        config: AdminEmailVerificationConfig,
        store: AdminEmailVerificationStoreProtocol,
        notification_service: AdminNotificationService | None = None,
        audit_service: AdminAuditLogServiceProtocol | None = None,
        cache: CacheBackendProtocol | None = None,
        resend_request_limit: int = 5,
        resend_window_seconds: int = 3600,
    ) -> None:
        """Initialise the verification service.

        Args:
            config: Email verification settings.
            store: Verification state persistence.
            notification_service: Optional delivery channel for the
                verification email (skipped when None).
            audit_service: Optional security audit logger.
            cache: Optional cache backend for per-IP resend rate limiting;
                ``None`` (or a failing cache) skips limiting (fail open).
            resend_request_limit: Max resend requests per IP per window.
            resend_window_seconds: Rate-limit window length in seconds.
        """
        self._config = config
        self._store = store
        self._notification_service = notification_service
        self._audit_service = audit_service
        self._cache = cache
        self._resend_request_limit = resend_request_limit
        self._resend_window_seconds = resend_window_seconds

    async def is_verified(self, user_id: str) -> bool:
        """Return True when the user's email is verified.

        Args:
            user_id: Admin user UUID.
        """
        return await self._store.is_verified(user_id)

    async def is_required(self, user_id: str) -> bool:
        """Return True when login must be gated on email verification.

        Args:
            user_id: Admin user UUID.
        """
        if not self._config.enabled or not self._config.enforcement:
            return False
        return not await self._store.is_verified(user_id)

    async def send_verification(
        self,
        user_id: str,
        email: str,
        user_name: str,
        base_url: str = "",
        ip_address: str = "",
        admin_prefix: str = "/admin",
    ) -> Result[None, AdminAuthError]:
        """Issue a verification link and email it to the user.

        No-op (Ok) when the flow is disabled or the email is already
        verified.  Delivery failures are NOT swallowed: a missing
        notification service or a failed delivery returns
        ``Err(AdminAuthError)`` with guidance on the missing mailer
        dependency.  Resend requests are rate limited per IP when a cache
        backend is wired (fail open).

        Args:
            user_id: Admin user UUID.
            email: Email address to verify.
            user_name: Display name for the email greeting.
            base_url: Origin used to build the absolute verify link
                (e.g. ``https://panel.example.com``).
            ip_address: Client IP for resend rate limiting.
            admin_prefix: Configured admin mount, without the origin.

        Returns:
            ``Ok(None)`` when the link was issued and delivered.
            ``Err(RateLimitExceededError)`` when this IP exceeds the
            resend limit.
            ``Err(AdminAuthError)`` when no notification service is bound
            or email delivery failed (e.g. no mailer backend configured).
        """
        if not self._config.enabled or await self._store.is_verified(user_id):
            return Ok(None)

        if self._cache is not None and await self._is_rate_limited(ip_address):
            logger.warning("email_verification_rate_limited", ip=ip_address)
            return Err(
                RateLimitExceededError(
                    "Too many verification emails. Please try again later.",
                    reason="rate_limit",
                )
            )

        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = datetime.now(UTC) + timedelta(hours=self._config.token_ttl_hours)
        await self._store.save_token(user_id, token_hash, expires_at)

        prefix = f"/{admin_prefix.strip('/')}" if admin_prefix.strip("/") else "/admin"
        verify_url = f"{base_url.rstrip('/')}{prefix}/verify-email/{token}"

        if self._notification_service is None:
            logger.error(
                "email_verification_skipped",
                user_id=user_id,
                email=email,
                verify_url=verify_url,
            )
            if self._audit_service is not None:
                await self._audit_service.log_event(
                    event_type=AdminSecurityEventType.EMAIL_VERIFICATION_SENT,
                    ip_address="",
                    user_agent="",
                    success=False,
                    admin_user_id=user_id,
                    metadata={"email": email, "reason": "no_notification_service"},
                )
            return Err(
                AdminAuthError(
                    "Verification email could not be delivered because no "
                    "notification/mailer dependency is configured. Configure a "
                    "mailer backend (lexigram-notification MailerModule with "
                    "driver 'smtp'/'sendgrid', or 'console' in development) "
                    "and retry.",
                )
            )

        result = await self._notification_service.notify_email_verification(
            user_email=email,
            user_name=user_name,
            verify_url=verify_url,
            expires_in=f"{self._config.token_ttl_hours} hours",
        )
        if result.is_err():
            logger.error(
                "email_verification_send_failed",
                user_id=user_id,
                email=email,
                error=str(result.unwrap_err()),
                verify_url=verify_url,
            )
            if self._audit_service is not None:
                await self._audit_service.log_event(
                    event_type=AdminSecurityEventType.EMAIL_VERIFICATION_SENT,
                    ip_address="",
                    user_agent="",
                    success=False,
                    admin_user_id=user_id,
                    metadata={"email": email, "reason": str(result.unwrap_err())},
                )
            return Err(
                AdminAuthError(
                    "Verification email could not be delivered: "
                    f"{result.unwrap_err()} Configure a mailer backend "
                    "(lexigram-notification MailerModule with driver "
                    "'smtp'/'sendgrid', or 'console' in development) and "
                    "retry.",
                )
            )

        if self._audit_service is not None:
            await self._audit_service.log_event(
                event_type=AdminSecurityEventType.EMAIL_VERIFICATION_SENT,
                ip_address="",
                user_agent="",
                success=True,
                admin_user_id=user_id,
                metadata={"email": email},
            )
        return Ok(None)

    async def verify_token(self, token: str) -> Result[bool, AdminAuthError]:
        """Validate and consume a verification token.

        Args:
            token: Raw token from the emailed link.

        Returns:
            ``Ok(True)`` when the token was valid and the email is now
            verified; ``Err(EmailVerificationTokenInvalidError)`` when the
            token is unknown, used, or expired.
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        user_id = await self._store.find_user_by_token_hash(token_hash)

        if user_id is None:
            await self._audit_failure("no_such_token")
            return Err(
                EmailVerificationTokenInvalidError(
                    "Invalid or expired verification link."
                )
            )

        consumed = await self._store.consume_token(user_id, token_hash)
        if not consumed:
            await self._audit_failure("consumed_or_expired", user_id)
            return Err(
                EmailVerificationTokenInvalidError(
                    "Invalid or expired verification link."
                )
            )

        if self._audit_service is not None:
            await self._audit_service.log_event(
                event_type=AdminSecurityEventType.EMAIL_VERIFIED,
                ip_address="",
                user_agent="",
                success=True,
                admin_user_id=user_id,
            )
        return Ok(True)

    async def mark_verified(self, user_id: str) -> None:
        """Mark a user's email verified without sending a verification link.

        Used when email ownership is proven out-of-band — the setup wizard's
        first admin presented the deployment setup token, so gating that
        account on an emailed link (possibly with no mailer configured yet)
        would lock the operator out of a fresh install.

        Args:
            user_id: Admin user UUID.
        """
        await self._store.mark_verified(user_id)
        if self._audit_service is not None:
            await self._audit_service.log_event(
                event_type=AdminSecurityEventType.EMAIL_VERIFIED,
                ip_address="",
                user_agent="",
                success=True,
                admin_user_id=user_id,
                metadata={"reason": "out_of_band_setup"},
            )

    async def resend_verification(
        self,
        user_id: str,
        email: str,
        user_name: str,
        base_url: str = "",
        ip_address: str = "",
        admin_prefix: str = "/admin",
    ) -> Result[None, AdminAuthError]:
        """Re-issue and re-send the verification email.

        Args:
            user_id: Admin user UUID.
            email: Email address to verify.
            user_name: Display name for the email greeting.
            base_url: Origin used to build the absolute verify link.
            ip_address: Client IP for resend rate limiting.
            admin_prefix: Configured admin mount, without the origin.

        Returns:
            ``Ok(None)`` on success or when the flow is disabled/verified.
        """
        return await self.send_verification(
            user_id,
            email,
            user_name,
            base_url,
            ip_address,
            admin_prefix,
        )

    async def _is_rate_limited(self, ip_address: str) -> bool:
        """Check and increment the per-IP resend counter. Fail open.

        Uses a fixed-window counter keyed by a sha256 hash of the client IP
        (avoids PII in cache key listings). Any cache failure is treated as
        "not limited" so a cache outage never blocks verification emails.

        Args:
            ip_address: Client IP address.

        Returns:
            ``True`` when the IP exceeds ``resend_request_limit``.
        """
        try:
            ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()[:16]
            key = f"admin:email-verification:ip:{ip_hash}"
            cache = self._cache
            if cache is None:
                return False
            result = await cache.get(key)
            value = result.unwrap() if result.is_ok() else None
            count = int(value) if value else 0
            if count >= self._resend_request_limit:
                return True
            await cache.set(key, str(count + 1), ttl=self._resend_window_seconds)
            return False
        except Exception:  # noqa: BLE001 — fail open on cache outages
            logger.warning("email_verification_rate_limit_unavailable")
            return False

    async def _audit_failure(self, reason: str, user_id: str | None = None) -> None:
        """Record a failed verification attempt (never raises)."""
        if self._audit_service is None:
            return
        await self._audit_service.log_event(
            event_type=AdminSecurityEventType.EMAIL_VERIFICATION_FAILED,
            ip_address="",
            user_agent="",
            success=False,
            admin_user_id=user_id,
            metadata={"reason": reason},
        )


__all__ = ["AdminEmailVerificationService"]
