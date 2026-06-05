"""Admin email one-time-password (login factor) service.

Handles issuing, delivering, and consuming emailed 6-digit codes used as
the config-chosen second factor.  Depends only on
``AdminEmailOtpStoreProtocol`` from ``lexigram.admin.auth.protocols``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import secrets
from typing import TYPE_CHECKING

from lexigram.admin.auth.errors import (
    EmailOtpCooldownError,
    EmailOtpDeliveryError,
    MfaNotEnabledError,
)
from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.config import AdminEmailOtpConfig
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.admin.auth.errors import AdminAuthError
    from lexigram.admin.auth.protocols import (
        AdminAuditLogServiceProtocol,
        AdminEmailOtpStoreProtocol,
    )
    from lexigram.admin.services.notifications import AdminNotificationService

logger = get_logger(__name__)


@inject
class AdminEmailOtpService:
    """Email OTP factor: issue, deliver, and verify 6-digit codes.

    Codes are stored only as sha256 digests and consumed atomically
    (single-use, expiring).  Unlike verification emails, delivery failure is
    NOT fail-open — the factor is unusable without a working mailer, so the
    service returns ``Err(EmailOtpDeliveryError)`` instead.
    """

    def __init__(
        self,
        config: AdminEmailOtpConfig,
        store: AdminEmailOtpStoreProtocol,
        notification_service: AdminNotificationService | None = None,
        audit_service: AdminAuditLogServiceProtocol | None = None,
    ) -> None:
        """Initialise the email OTP service.

        Args:
            config: Email OTP settings (TTL, resend cooldown).
            store: Code persistence.
            notification_service: Delivery channel for the emailed code.
            audit_service: Optional security audit logger.
        """
        self._config = config
        self._store = store
        self._notification_service = notification_service
        self._audit_service = audit_service

    async def send_otp(
        self,
        user_id: str,
        email: str,
        user_name: str,
    ) -> Result[None, AdminAuthError]:
        """Generate, persist, and email a fresh one-time code.

        Args:
            user_id: Admin user UUID.
            email: Email address to send the code to.
            user_name: Display name for the email greeting.

        Returns:
            ``Ok(None)`` on success; ``Err(MfaNotEnabledError)`` when the
            factor is disabled, ``Err(EmailOtpCooldownError)`` when a resend
            is attempted too soon, ``Err(EmailOtpDeliveryError)`` when the
            code cannot be delivered.
        """
        if not self._config.enabled:
            return Err(MfaNotEnabledError("Email OTP is not enabled."))

        last_sent_at = await self._store.last_sent_at(user_id)
        if last_sent_at is not None:
            elapsed = (datetime.now(UTC) - last_sent_at).total_seconds()
            if elapsed < self._config.resend_cooldown_seconds:
                return Err(
                    EmailOtpCooldownError(
                        "Please wait before requesting another code."
                    )
                )

        code = f"{secrets.randbelow(900000) + 100000}"
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        expires_at = datetime.now(UTC) + timedelta(minutes=self._config.ttl_minutes)
        await self._store.save(user_id, code_hash, expires_at)

        if self._notification_service is None:
            await self._audit_failure(user_id, "no_mailer")
            return Err(
                EmailOtpDeliveryError(
                    "No email delivery service is configured."
                )
            )

        result = await self._notification_service.notify_email_otp(
            user_email=email,
            user_name=user_name,
            code=code,
            expires_in=f"{self._config.ttl_minutes} minutes",
        )
        if result.is_err():
            error = str(result.unwrap_err())
            await self._audit_failure(user_id, error)
            return Err(EmailOtpDeliveryError(error))

        if self._audit_service is not None:
            await self._audit_service.log_event(
                event_type=AdminSecurityEventType.EMAIL_OTP_SENT,
                ip_address="",
                user_agent="",
                success=True,
                admin_user_id=user_id,
                metadata={"email": email},
            )
        return Ok(None)

    async def verify_otp(
        self, user_id: str, code: str
    ) -> Result[bool, AdminAuthError]:
        """Verify a code and consume it when valid.

        Args:
            user_id: Admin user UUID.
            code: 6-digit code from the email.

        Returns:
            ``Ok(True)`` when the code matched and was consumed;
            ``Ok(False)`` when it did not; ``Err(MfaNotEnabledError)`` when
            the factor is disabled.
        """
        if not self._config.enabled:
            return Err(MfaNotEnabledError("Email OTP is not enabled."))

        code_hash = hashlib.sha256(code.encode()).hexdigest()
        consumed = await self._store.consume(user_id, code_hash)
        if not consumed:
            await self._audit_failure(user_id, "invalid_code")
            return Ok(False)
        return Ok(True)

    async def _audit_failure(self, user_id: str, reason: str) -> None:
        """Record a failed OTP send/verify attempt (never raises)."""
        if self._audit_service is None:
            return
        await self._audit_service.log_event(
            event_type=AdminSecurityEventType.EMAIL_OTP_FAILED,
            ip_address="",
            user_agent="",
            success=False,
            admin_user_id=user_id,
            metadata={"reason": reason},
        )


__all__ = ["AdminEmailOtpService"]
