"""Email sending utilities for admin notifications."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.mailer import EmailMessage
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.admin.services.notifications.models import NotificationRecipient
    from lexigram.contracts.mailer.protocols import MailerProtocol

logger = get_logger(__name__)


class EmailSender:
    """Handles sending of notification emails via a MailerProtocol backend."""

    def __init__(
        self,
        mailer: MailerProtocol | None = None,
        from_email: str = "admin@example.com",
        from_name: str = "Admin System",
    ):
        """Initialize email sender.

        Args:
            mailer: MailerProtocol backend for email delivery; no-ops when None.
            from_email: Default from email address.
            from_name: Default from name.
        """
        self.mailer = mailer
        self.from_email = from_email
        self.from_name = from_name

    async def send_email(
        self,
        recipient: NotificationRecipient,
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> None:
        """Send email to recipient.

        Args:
            recipient: Email recipient.
            subject: Email subject.
            body: Plain text body.
            html_body: Optional HTML body.

        Raises:
            RuntimeError: If email sending fails.
        """
        if self.mailer:
            message = EmailMessage(
                to=[recipient.email],
                subject=subject,
                body=body,
                html_body=html_body,
                from_email=self.from_email,
                from_name=self.from_name,
            )
            result = await self.mailer.send(message)
            if result.is_err():
                raise RuntimeError(str(result.unwrap_err()))
        else:
            logger.info(
                "notification_email_skipped",
                to=recipient.email,
                subject=subject,
            )


__all__ = ["EmailSender"]
