"""Admin notification service - main orchestration class."""

from __future__ import annotations

from datetime import UTC, datetime
import time
from typing import Any

from lexigram.admin.config import AdminNotificationConfig
from lexigram.admin.exceptions import NotificationError
from lexigram.admin.services.notifications.models import (
    Notification,
    NotificationRecipient,
    NotificationResult,
    NotificationType,
)
from lexigram.admin.services.notifications.sender import EmailSender
from lexigram.admin.services.notifications.templates import TemplateRenderer
from lexigram.contracts.mailer.protocols import MailerProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)


@inject
class AdminNotificationService:
    """Service for sending admin notifications.

    Integrates with lexigram.messaging for email delivery
    and provides admin-specific templates and functionality.

    Example:
        >>> service = AdminNotificationService(messaging, config)
        >>>
        >>> # Send user created notification
        >>> await service.notify_user_created(
        ...     user=user,
        ...     created_by=admin,
        ...     recipients=admin_list,
        ... )
        >>>
        >>> # Send bulk completion notification
        >>> await service.notify_bulk_completed(
        ...     operation="delete",
        ...     resource="users",
        ...     total=100,
        ...     successful=98,
        ...     failed=2,
        ...     recipients=[admin],
        ... )
    """

    def __init__(
        self,
        mailer: MailerProtocol | None = None,
        config: AdminNotificationConfig | None = None,
    ):
        self.config = config or AdminNotificationConfig()

        # Initialize components
        app_name: str = (
            getattr(self.config, "app_name", None)
            or getattr(self.config, "email_from_name", "Admin")
            or "Admin"
        )
        self.template_renderer = TemplateRenderer(app_name)
        self.email_sender = EmailSender(
            mailer=mailer,
            from_email=self.config.email_from,
            from_name=self.config.email_from_name,
        )

        self._sent_count = 0

        # Settings-panel overrides (R39, doc 35): attached best-effort at
        # mount time; sender identity re-resolved on a monotonic TTL so
        # panel saves apply without a restart (R37 pattern).
        self._settings_store: Any = None
        self._settings_ttl: float = 30.0
        self._identity_refreshed_at: float | None = None
        # Delivery log (R46, doc 42): attached best-effort at mount time.
        self._delivery_log: Any = None

    # ------------------------------------------------------------------
    # Delivery log (R46 — docs/09-01-2026/42-email-delivery-log.md)
    # ------------------------------------------------------------------

    def attach_delivery_log(self, store: Any) -> None:
        """Attach a persistent delivery log (AdminEmailLogSqlStore-like).

        Args:
            store: Object with ``async record(notification_type, recipient,
                subject, success, error)``.
        """
        self._delivery_log = store

    async def _log_delivery(
        self,
        notification_type: Any,
        recipient: str,
        subject: str,
        success: bool,
        error: str | None = None,
    ) -> None:
        """Best-effort delivery-log append — must never break a send."""
        if self._delivery_log is None:
            return
        try:
            await self._delivery_log.record(
                notification_type=str(
                    getattr(notification_type, "value", notification_type)
                ),
                recipient=recipient,
                subject=subject,
                success=success,
                error=error,
            )
        except Exception:  # noqa: BLE001 — a broken log must never break a send
            logger.warning("notification.delivery_log_failed")

    # ------------------------------------------------------------------
    # Settings overrides (R39 — docs/09-01-2026/35-notification-settings.md)
    # ------------------------------------------------------------------

    def attach_settings_store(self, store: Any, ttl: float = 30.0) -> None:
        """Attach a settings store for panel-editable sender identity.

        Args:
            store: StoreBase-like object with ``async get(key)``.
            ttl: Seconds between refreshes; ``<= 0`` refreshes every send.
        """
        self._settings_store = store
        self._settings_ttl = ttl
        self._identity_refreshed_at = None

    def _identity_fresh(self) -> bool:
        """True while the last identity refresh is within the TTL."""
        return (
            self._identity_refreshed_at is not None
            and self._settings_ttl > 0
            and time.monotonic() - self._identity_refreshed_at < self._settings_ttl
        )

    async def _refresh_sender_identity(self) -> None:
        """Apply ``admin.notifications.*`` overrides to the email sender.

        Non-empty values override the sender identity; empty/absent values
        reset to the config defaults (clearing a panel field undoes the
        override). Read errors keep the current identity and advance the
        retry timestamp so a flapping store is not hammered per send.
        """
        if self._settings_store is None or self._identity_fresh():
            return
        try:
            email_from = await self._settings_store.get(
                "admin.notifications.email_from"
            )
            from_name = await self._settings_store.get(
                "admin.notifications.email_from_name"
            )
        except Exception:  # noqa: BLE001 — stale identity over broken sends
            logger.warning("admin.notifications.settings_read_failed")
            self._identity_refreshed_at = time.monotonic()
            return
        self.email_sender.from_email = (
            str(email_from).strip()
            if email_from and str(email_from).strip()
            else self.config.email_from
        )
        self.email_sender.from_name = (
            str(from_name).strip()
            if from_name and str(from_name).strip()
            else self.config.email_from_name
        )
        self._identity_refreshed_at = time.monotonic()

    async def effective_sender(self) -> tuple[str, str]:
        """Return the ``(from_email, from_name)`` outbound emails carry now."""
        await self._refresh_sender_identity()
        return self.email_sender.from_email, self.email_sender.from_name

    async def mailer_health(self) -> Any | None:
        """Best-effort backend health check for the status card.

        Returns the backend's ``HealthCheckResult`` when it exposes
        ``health_check()``; ``None`` when no mailer is bound, the backend
        lacks the method, or the check raises (logged, never rendered).
        """
        mailer = self.email_sender.mailer
        check = getattr(mailer, "health_check", None) if mailer else None
        if not callable(check):
            return None
        try:
            return await check()
        except Exception:  # noqa: BLE001 — diagnostics must not break the page
            logger.warning(
                "admin.notifications.health_check_failed",
                backend=type(mailer).__name__,
            )
            return None

    async def send(
        self,
        notification: Notification,
    ) -> Result[NotificationResult, NotificationError]:
        """Send a notification.

        Args:
            notification: Notification to send

        Returns:
            ``Ok(NotificationResult)`` on success or partial success.
            ``Err(NotificationError)`` when all recipients failed.
        """
        await self._refresh_sender_identity()
        enabled_types = getattr(self.config, "enabled_types", None)
        if enabled_types and notification.type not in enabled_types:
            # Visible in the delivery log: a silently disabled type is the
            # exact "where did my email go" case (R46, doc 42 §2.2).
            for recipient in notification.recipients:
                await self._log_delivery(
                    notification.type,
                    recipient.email,
                    notification.subject,
                    success=False,
                    error="Notification type not enabled",
                )
            result = NotificationResult(
                notification_id=notification.id,
                recipients_sent=0,
                errors=["Notification type not enabled"],
            )
            return Ok(result)

        sent = 0
        failed = 0
        errors: list[str] = []

        for recipient in notification.recipients:
            # Check recipient preferences
            if not recipient.can_receive(notification.type):
                continue

            # Send via channels
            for channel in notification.channels:
                if channel.value == "email":  # Use .value to compare with string
                    try:
                        await self.email_sender.send_email(
                            recipient=recipient,
                            subject=notification.subject,
                            body=notification.body,
                            html_body=notification.html_body,
                        )
                        sent += 1
                        await self._log_delivery(
                            notification.type,
                            recipient.email,
                            notification.subject,
                            success=True,
                        )
                    except (RuntimeError, OSError, ConnectionError) as e:
                        failed += 1
                        errors.append(f"Email to {recipient.email}: {e}")
                        await self._log_delivery(
                            notification.type,
                            recipient.email,
                            notification.subject,
                            success=False,
                            error=str(e),
                        )

        result = NotificationResult(
            notification_id=notification.id,
            recipients_sent=sent,
            recipients_failed=failed,
            errors=errors,
        )

        if sent == 0 and failed > 0:
            return Err(
                NotificationError(
                    f"All {failed} recipient(s) failed: {'; '.join(errors)}"
                )
            )

        return Ok(result)

    # ========================================================================
    # Convenience Methods
    # ========================================================================

    async def notify_user_created(
        self,
        user: Any,
        created_by: Any,
        recipients: list[NotificationRecipient],
    ) -> Result[NotificationResult, NotificationError]:
        """Send user created notification."""
        data = {
            "user_name": getattr(user, "name", str(user)),
            "user_email": getattr(user, "email", ""),
            "user_role": getattr(user, "role", "User"),
            "created_by": getattr(created_by, "name", str(created_by)),
            "created_at": datetime.now(UTC).isoformat(),
            "user_url": f"{getattr(self.config, 'base_url', '')}/users/{getattr(user, 'id', '')}",
        }

        subject, body, html_body = self.template_renderer.render_template(
            NotificationType.USER_CREATED,
            data,
        )

        notification = Notification(
            type=NotificationType.USER_CREATED,
            subject=subject,
            body=body,
            html_body=html_body,
            recipients=recipients,
            data=data,
        )

        return await self.send(notification)

    async def notify_user_invited(
        self,
        user_email: str,
        user_name: str,
        invite_url: str,
        expires_in: str = "7 days",
    ) -> Result[NotificationResult, NotificationError]:
        """Send user invitation notification."""
        data = {
            "user_name": user_name,
            "user_email": user_email,
            "invite_url": invite_url,
            "expires_in": expires_in,
        }

        subject, body, html_body = self.template_renderer.render_template(
            NotificationType.USER_INVITED,
            data,
        )

        recipient = NotificationRecipient(email=user_email, name=user_name)

        notification = Notification(
            type=NotificationType.USER_INVITED,
            subject=subject,
            body=body,
            html_body=html_body,
            recipients=[recipient],
            data=data,
        )

        return await self.send(notification)

    async def notify_password_reset(
        self,
        user_email: str,
        user_name: str,
        reset_url: str,
        expires_in: str = "1 hour",
    ) -> Result[NotificationResult, NotificationError]:
        """Send password reset notification."""
        data = {
            "user_name": user_name,
            "reset_url": reset_url,
            "expires_in": expires_in,
        }

        subject, body, html_body = self.template_renderer.render_template(
            NotificationType.PASSWORD_RESET,
            data,
        )

        recipient = NotificationRecipient(email=user_email, name=user_name)

        notification = Notification(
            type=NotificationType.PASSWORD_RESET,
            subject=subject,
            body=body,
            html_body=html_body,
            recipients=[recipient],
            data=data,
        )

        return await self.send(notification)

    async def notify_email_verification(
        self,
        user_email: str,
        user_name: str,
        verify_url: str,
        expires_in: str = "24 hours",
    ) -> Result[NotificationResult, NotificationError]:
        """Send email verification notification."""
        data = {
            "user_name": user_name,
            "verify_url": verify_url,
            "expires_in": expires_in,
        }

        subject, body, html_body = self.template_renderer.render_template(
            NotificationType.EMAIL_VERIFICATION,
            data,
        )

        recipient = NotificationRecipient(email=user_email, name=user_name)

        notification = Notification(
            type=NotificationType.EMAIL_VERIFICATION,
            subject=subject,
            body=body,
            html_body=html_body,
            recipients=[recipient],
            data=data,
        )

        return await self.send(notification)

    async def notify_email_otp(
        self,
        user_email: str,
        user_name: str,
        code: str,
        expires_in: str = "10 minutes",
    ) -> Result[NotificationResult, NotificationError]:
        """Send email one-time-password notification."""
        data = {
            "user_name": user_name,
            "code": code,
            "expires_in": expires_in,
        }

        subject, body, html_body = self.template_renderer.render_template(
            NotificationType.EMAIL_OTP,
            data,
        )

        recipient = NotificationRecipient(email=user_email, name=user_name)

        notification = Notification(
            type=NotificationType.EMAIL_OTP,
            subject=subject,
            body=body,
            html_body=html_body,
            recipients=[recipient],
            data=data,
        )

        return await self.send(notification)

    async def notify_bulk_started(
        self,
        operation_name: str,
        resource: str,
        total_items: int,
        started_by: Any,
        recipients: list[NotificationRecipient],
    ) -> Result[NotificationResult, NotificationError]:
        """Send bulk operation started notification."""
        data = {
            "operation_name": operation_name,
            "resource": resource,
            "total_items": total_items,
            "started_by": getattr(started_by, "name", str(started_by)),
            "started_at": datetime.now(UTC).isoformat(),
        }

        subject, body, html_body = self.template_renderer.render_template(
            NotificationType.BULK_STARTED,
            data,
        )

        notification = Notification(
            type=NotificationType.BULK_STARTED,
            subject=subject,
            body=body,
            html_body=html_body,
            recipients=recipients,
            data=data,
        )

        return await self.send(notification)

    async def notify_bulk_completed(
        self,
        operation_name: str,
        resource: str,
        total_items: int,
        successful: int,
        failed: int,
        duration: str,
        recipients: list[NotificationRecipient],
        results_url: str | None = None,
    ) -> Result[NotificationResult, NotificationError]:
        """Send bulk operation completed notification."""
        data = {
            "operation_name": operation_name,
            "resource": resource,
            "total_items": total_items,
            "successful": successful,
            "failed": failed,
            "duration": duration,
            "results_url": results_url
            or f"{getattr(self.config, 'base_url', '')}/{resource}",
        }

        subject, body, html_body = self.template_renderer.render_template(
            NotificationType.BULK_COMPLETED,
            data,
        )

        notification = Notification(
            type=NotificationType.BULK_COMPLETED,
            subject=subject,
            body=body,
            html_body=html_body,
            recipients=recipients,
            data=data,
        )

        return await self.send(notification)

    async def notify_bulk_failed(
        self,
        operation_name: str,
        resource: str,
        error_message: str,
        processed: int,
        recipients: list[NotificationRecipient],
    ) -> Result[NotificationResult, NotificationError]:
        """Send bulk operation failed notification."""
        data = {
            "operation_name": operation_name,
            "resource": resource,
            "error_message": error_message,
            "processed": processed,
        }

        subject, body, html_body = self.template_renderer.render_template(
            NotificationType.BULK_FAILED,
            data,
        )

        notification = Notification(
            type=NotificationType.BULK_FAILED,
            subject=subject,
            body=body,
            html_body=html_body,
            recipients=recipients,
            data=data,
        )

        return await self.send(notification)

    async def notify_export_ready(
        self,
        export_name: str,
        file_format: str,
        record_count: int,
        file_size: str,
        download_url: str,
        recipient: NotificationRecipient,
        expires_in: str = "24 hours",
    ) -> Result[NotificationResult, NotificationError]:
        """Send export ready notification."""
        data = {
            "export_name": export_name,
            "format": file_format,
            "record_count": record_count,
            "file_size": file_size,
            "download_url": download_url,
            "expires_in": expires_in,
        }

        subject, body, html_body = self.template_renderer.render_template(
            NotificationType.EXPORT_READY,
            data,
        )

        notification = Notification(
            type=NotificationType.EXPORT_READY,
            subject=subject,
            body=body,
            html_body=html_body,
            recipients=[recipient],
            data=data,
        )

        return await self.send(notification)

    async def notify_system_alert(
        self,
        alert_title: str,
        alert_message: str,
        severity: str,
        component: str,
        recipients: list[NotificationRecipient],
    ) -> Result[NotificationResult, NotificationError]:
        """Send system alert notification."""
        severity_map = {
            "info": "info",
            "warning": "warning",
            "error": "error",
            "critical": "error",
        }

        data = {
            "alert_title": alert_title,
            "alert_message": alert_message,
            "severity": severity.upper(),
            "severity_class": severity_map.get(severity.lower(), "warning"),
            "component": component,
            "occurred_at": datetime.now(UTC).isoformat(),
        }

        subject, body, html_body = self.template_renderer.render_template(
            NotificationType.SYSTEM_ALERT,
            data,
        )

        notification = Notification(
            type=NotificationType.SYSTEM_ALERT,
            subject=subject,
            body=body,
            html_body=html_body,
            recipients=recipients,
            data=data,
            priority="high" if severity.lower() in ("error", "critical") else "normal",
        )

        return await self.send(notification)

    # ------------------------------------------------------------------
    # Diagnostics (roadmap R11 — docs/09-01-2026/07-mailer-onboarding.md)
    # ------------------------------------------------------------------

    @property
    def mailer_bound(self) -> bool:
        """True when a ``MailerProtocol`` backend is wired for delivery."""
        return self.email_sender.mailer is not None

    @property
    def mailer_backend_name(self) -> str | None:
        """Class name of the bound mailer backend, or ``None``."""
        mailer = self.email_sender.mailer
        return type(mailer).__name__ if mailer is not None else None

    @property
    def mailer_is_debug_fallback(self) -> bool:
        """True when the bound backend is the automatic debug console mailer."""
        return getattr(self.email_sender.mailer, "is_debug_fallback", False) is True

    async def notify_test_email(
        self,
        recipient: NotificationRecipient,
    ) -> Result[NotificationResult, NotificationError]:
        """Send a diagnostics test email straight through the mailer.

        Deliberately bypasses recipient preferences and ``enabled_types``
        gating so configuration filters can never mask a delivery problem
        — this is an operator diagnostics path, not a product notification.

        Args:
            recipient: The recipient (the acting admin's own address).

        Returns:
            ``Ok(NotificationResult)`` when the backend accepted the send;
            ``Err(NotificationError)`` when no mailer is bound or the
            backend rejected/failed the delivery.
        """
        if not self.mailer_bound:
            return Err(
                NotificationError(
                    "No mailer backend is configured. Bind a MailerProtocol "
                    "(or enable debug mode for the console fallback)."
                )
            )
        await self._refresh_sender_identity()
        subject = "Test email from Lexigram Admin"
        body = (
            "This is a test email sent from the Email delivery page.\n\n"
            "If you are reading this, outbound email delivery works."
        )
        try:
            await self.email_sender.send_email(
                recipient=recipient,
                subject=subject,
                body=body,
            )
        except (RuntimeError, OSError, ConnectionError) as exc:
            await self._log_delivery(
                "test_email", recipient.email, subject, success=False, error=str(exc)
            )
            return Err(NotificationError(f"Test email failed: {exc}"))
        self._sent_count += 1
        await self._log_delivery("test_email", recipient.email, subject, success=True)
        return Ok(NotificationResult(recipients_sent=1))


__all__ = ["AdminNotificationService"]
