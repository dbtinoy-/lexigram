"""Send-email-batch task handler.

Processes a single batch of email recipients for a campaign.  The handler
uses constructor injection to receive a stub mailer protocol so it can be
swapped in tests without changing any business logic.

Pattern demonstrated:
- Class-based handler with ``__init__`` constructor injection
- ``Result[T, E]`` return type for expected failure paths
- Structured logging with key-value pairs
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from lexigram.contracts.exceptions.domain import DomainError
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

from lexigram_example_worker.domain.campaign import CampaignPayload

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Payload / result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EmailBatchPayload:
    """Input for a single email batch send.

    Attributes:
        campaign_id: Originating campaign identifier.
        subject: Email subject line.
        body_html: HTML body content.
        recipient_ids: Slice of recipient identifiers for this batch.
    """

    campaign_id: str
    subject: str
    body_html: str
    recipient_ids: list[str] = field(default_factory=list)

    @classmethod
    def from_campaign(
        cls,
        payload: CampaignPayload,
        batch: list[str],
    ) -> EmailBatchPayload:
        """Create a batch payload from a campaign payload slice.

        Args:
            payload: The originating campaign payload.
            batch: Subset of ``recipient_ids`` for this batch.

        Returns:
            An :class:`EmailBatchPayload` for the given batch.
        """
        return cls(
            campaign_id=payload.campaign_id,
            subject=payload.subject,
            body_html=payload.body_html,
            recipient_ids=list(batch),
        )


@dataclass(frozen=True)
class BatchResult:
    """Outcome of a successful email batch send.

    Attributes:
        campaign_id: Campaign this batch belongs to.
        sent: Number of emails successfully dispatched.
        failed_ids: Recipient IDs that could not be reached.
    """

    campaign_id: str
    sent: int
    failed_ids: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Mailer protocol (contract boundary — never import a concrete mailer here)
# ---------------------------------------------------------------------------


class MailerProtocol(Protocol):
    """Minimal async mailer contract used by :class:`SendEmailBatchHandler`.

    Real implementations live in ``lexigram-notification`` or an app-level
    adapter.  Tests inject a ``FakeMailer`` that records calls.
    """

    async def send(
        self,
        recipient_id: str,
        subject: str,
        body_html: str,
    ) -> bool:
        """Send one email.

        Args:
            recipient_id: Identifier of the recipient.
            subject: Email subject line.
            body_html: HTML body content.

        Returns:
            ``True`` if the send succeeded; ``False`` on a soft failure.
        """
        ...


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


class SendEmailBatchHandler:
    """Processes a batch of email recipients for a campaign.

    Receives a :class:`MailerProtocol` via constructor injection so the
    underlying transport can be swapped without modifying this class.

    Args:
        mailer: Async mailer implementation satisfying :class:`MailerProtocol`.
    """

    def __init__(self, mailer: MailerProtocol) -> None:
        self._mailer = mailer

    async def execute(
        self,
        payload: EmailBatchPayload,
    ) -> Result[BatchResult, DomainError]:
        """Send all emails in *payload* and return an aggregated result.

        Validates the payload, iterates recipients, and delegates each send
        to the injected mailer.  Soft-failures (``mailer.send`` returns
        ``False``) are collected but do not abort the batch.

        Args:
            payload: Batch definition — recipients, subject, body.

        Returns:
            ``Ok(BatchResult)`` when the batch completes (even with partial
            failures); ``Err(DomainError)`` for hard validation errors.
        """
        if not payload.recipient_ids:
            return Err(
                DomainError(
                    "recipient_ids cannot be empty",
                    details={"campaign_id": payload.campaign_id},
                )
            )

        logger.info(
            "send_email_batch.started",
            campaign_id=payload.campaign_id,
            recipient_count=len(payload.recipient_ids),
        )

        sent = 0
        failed_ids: list[str] = []

        for recipient_id in payload.recipient_ids:
            success = await self._mailer.send(
                recipient_id=recipient_id,
                subject=payload.subject,
                body_html=payload.body_html,
            )
            if success:
                sent += 1
            else:
                failed_ids.append(recipient_id)
                logger.warning(
                    "send_email_batch.recipient_failed",
                    campaign_id=payload.campaign_id,
                    recipient_id=recipient_id,
                )

        result = BatchResult(
            campaign_id=payload.campaign_id,
            sent=sent,
            failed_ids=failed_ids,
        )

        logger.info(
            "send_email_batch.completed",
            campaign_id=payload.campaign_id,
            sent=sent,
            failed=len(failed_ids),
        )

        return Ok(result)


__all__ = [
    "BatchResult",
    "EmailBatchPayload",
    "MailerProtocol",
    "SendEmailBatchHandler",
]
