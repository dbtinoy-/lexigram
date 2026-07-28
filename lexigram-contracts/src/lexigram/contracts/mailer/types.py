# lexigram-contracts/src/lexigram/contracts/mailer/types.py
"""Mailer value types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

from lexigram.contracts.lib.time import utcnow as _utcnow

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class EmailMessage:
    """A cross-channel email message value object.

    Passed to :class:`~lexigram.contracts.mailer.protocols.MailerProtocol`.
    All fields except *to* and *subject* are optional to keep simple use
    cases concise.

    Attributes:
        to: List of recipient email addresses.
        subject: Email subject line.
        body: Plain-text message body.
        html_body: HTML message body; falls back to *body* when absent.
        from_email: Sender address; implementations should supply a
            safe default when ``None``.
        from_name: Human-readable sender name.
        reply_to: Optional reply-to address.
        cc: Carbon-copy recipients.
        bcc: Blind carbon-copy recipients.
        headers: Additional MIME headers.
    """

    to: list[str]
    subject: str
    body: str = ""
    html_body: str | None = None
    from_email: str | None = None
    from_name: str | None = None
    reply_to: str | None = None
    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class MessageDeliveryReceipt:
    """Confirmation that a message was accepted by the delivery backend.

    This is the success value returned by all messaging send operations.
    It does NOT guarantee delivery to the end recipient; it only confirms
    that the backend accepted the request.

    Attributes:
        message_id: Unique identifier for the message, assigned by the
            framework (or the backend when ``provider_reference`` differs).
        backend: Name of the backend that handled the send.
        channel: Delivery channel: ``"email"``, ``"sms"``, or ``"push"``.
        sent_at: UTC timestamp when the backend accepted the message.
        provider_reference: Opaque reference returned by the external
            provider. ``None`` when the backend does not return a reference.
    """

    message_id: str
    backend: str
    channel: str
    sent_at: datetime = field(default_factory=_utcnow)
    provider_reference: str | None = None


class MessagePriority(StrEnum):
    """Message delivery priority."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MessageStatus(StrEnum):
    """Outbound message status."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DeliveryState(StrEnum):
    """Downstream delivery state reported by provider."""

    QUEUED = "queued"
    DELIVERED = "delivered"
    BOUNCED = "bounced"
    REJECTED = "rejected"
    DEFERRED = "deferred"


@dataclass(frozen=True)
class MessageAddress:
    """An email address with an optional display name.

    Attributes:
        email: RFC-5321 email address.
        name: Human-readable display name; omitted when ``None``.
    """

    email: str
    name: str | None = None

    def __str__(self) -> str:
        if self.name:
            return f"{self.name} <{self.email}>"
        return self.email


@dataclass(frozen=True)
class Attachment:
    """An email attachment.

    Attributes:
        filename: Suggested filename shown to the recipient.
        content: Raw bytes of the attachment.
        content_type: MIME type; defaults to ``application/octet-stream``.
        content_id: Optional CID for inline embedding (e.g. ``cid:logo``).
    """

    filename: str
    content: bytes
    content_type: str = "application/octet-stream"
    content_id: str | None = None


__all__ = [
    "Attachment",
    "DeliveryState",
    "EmailMessage",
    "MessageAddress",
    "MessageDeliveryReceipt",
    "MessagePriority",
    "MessageStatus",
]
