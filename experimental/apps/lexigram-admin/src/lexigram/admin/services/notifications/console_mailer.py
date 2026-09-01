"""Console mailer fallback for admin development runs (roadmap R11).

A minimal :class:`~lexigram.contracts.mailer.protocols.MailerProtocol`
backend that logs every outgoing email instead of delivering it. It is
registered automatically — **in debug mode only** — when no real mailer
is bound (see ``di/sub_providers/auth_registrations.py``), so the
verification / password-reset / OTP flows are completable in local runs
by copying the emailed link from the server log.

The admin package deliberately does not depend on
``lexigram-notification``; this class is a self-contained implementation
against the contracts package. Design: docs/09-01-2026/07-mailer-onboarding.md.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import uuid

from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.contracts.mailer import EmailMessage, MessageDeliveryReceipt
from lexigram.logging import get_logger
from lexigram.result import Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.mailer.errors import MailerError

logger = get_logger(__name__)

__all__ = ["AdminConsoleMailer"]


class AdminConsoleMailer:
    """Log-only ``MailerProtocol`` backend for debug-mode admin runs.

    Never touches the network: the full message (subject, recipients,
    and body — including any verification or reset links) is emitted as
    a single structured log line. Every send is accepted.
    """

    #: Marks this backend as the automatic debug fallback so the Email
    #: delivery page can label it accordingly.
    is_debug_fallback = True

    async def send(
        self, message: EmailMessage
    ) -> Result[MessageDeliveryReceipt, MailerError]:
        """Log the email and return a synthetic acceptance receipt.

        Args:
            message: The email to log.

        Returns:
            ``Ok(MessageDeliveryReceipt)`` — the message is always accepted.
        """
        logger.info(
            "admin.console_mailer.email",
            to=list(message.to),
            subject=message.subject,
            from_email=getattr(message, "from_email", None),
            body=message.body,
        )
        return Ok(
            MessageDeliveryReceipt(
                message_id=str(uuid.uuid4()),
                backend="admin-console",
                channel="email",
            )
        )

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Always healthy — there is no backend to fail.

        Args:
            timeout: Ignored; kept for protocol compatibility.

        Returns:
            A healthy :class:`HealthCheckResult` for the console backend.
        """
        return HealthCheckResult(
            status=HealthStatus.HEALTHY,
            component="admin-console-mailer",
            message="Console mailer logs emails to the server log.",
        )
