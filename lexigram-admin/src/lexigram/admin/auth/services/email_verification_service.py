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

from lexigram.admin.auth.errors import EmailVerificationTokenInvalidError
from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.config import AdminEmailVerificationConfig
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.admin.auth.errors import AdminAuthError
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
    sha256 digest.  Delivery is fail-open: when no notification service is
    bound, sending is skipped (logged) and the flow still returns Ok so the
    panel remains usable — mirroring the password-reset behaviour.
    """

    def __init__(
        self,
        config: AdminEmailVerificationConfig,
        store: AdminEmailVerificationStoreProtocol,
        notification_service: AdminNotificationService | None = None,
        audit_service: AdminAuditLogServiceProtocol | None = None,
    ) -> None:
        """Initialise the verification service.

        Args:
            config: Email verification settings.
            store: Verification state persistence.
            notification_service: Optional delivery channel for the
                verification email (skipped when None).
            audit_service: Optional security audit logger.
        """
        self._config = config
        self._store = store
        self._notification_service = notification_service
        self._audit_service = audit_service

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
    ) -> Result[None, AdminAuthError]:
        """Issue a verification link and email it to the user.

        No-op (Ok) when the flow is disabled or the email is already
        verified.  Delivery is fail-open: missing notification service or a
        delivery failure only logs — the flow still returns Ok.

        Args:
            user_id: Admin user UUID.
            email: Email address to verify.
            user_name: Display name for the email greeting.
            base_url: Origin used to build the absolute verify link
                (e.g. ``https://panel.example.com``).

        Returns:
            ``Ok(None)`` always in the failure cases above; token is
            persisted before delivery so a later resend re-issues.
        """
        if not self._config.enabled or await self._store.is_verified(user_id):
            return Ok(None)

        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = datetime.now(UTC) + timedelta(hours=self._config.token_ttl_hours)
        await self._store.save_token(user_id, token_hash, expires_at)

        verify_url = f"{base_url.rstrip('/')}/admin/verify-email/{token}"

        if self._notification_service is None:
            logger.info(
                "email_verification_skipped",
                user_id=user_id,
                email=email,
            )
        else:
            result = await self._notification_service.notify_email_verification(
                user_email=email,
                user_name=user_name,
                verify_url=verify_url,
                expires_in=f"{self._config.token_ttl_hours} hours",
            )
            if result.is_err():
                logger.warning(
                    "email_verification_send_failed",
                    user_id=user_id,
                    email=email,
                    error=str(result.unwrap_err()),
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
            return Err(EmailVerificationTokenInvalidError("Invalid or expired verification link."))

        consumed = await self._store.consume_token(user_id, token_hash)
        if not consumed:
            await self._audit_failure("consumed_or_expired", user_id)
            return Err(EmailVerificationTokenInvalidError("Invalid or expired verification link."))

        if self._audit_service is not None:
            await self._audit_service.log_event(
                event_type=AdminSecurityEventType.EMAIL_VERIFIED,
                ip_address="",
                user_agent="",
                success=True,
                admin_user_id=user_id,
            )
        return Ok(True)

    async def resend_verification(
        self,
        user_id: str,
        email: str,
        user_name: str,
        base_url: str = "",
    ) -> Result[None, AdminAuthError]:
        """Re-issue and re-send the verification email.

        Args:
            user_id: Admin user UUID.
            email: Email address to verify.
            user_name: Display name for the email greeting.
            base_url: Origin used to build the absolute verify link.

        Returns:
            ``Ok(None)`` on success or when the flow is disabled/verified.
        """
        return await self.send_verification(user_id, email, user_name, base_url)

    async def _audit_failure(
        self, reason: str, user_id: str | None = None
    ) -> None:
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
