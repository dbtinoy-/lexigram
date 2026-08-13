# lexigram-contracts/src/lexigram/contracts/mailer/__init__.py
"""Mailer protocols, types, and errors."""

from __future__ import annotations

from lexigram.contracts.mailer.errors import MailerError
from lexigram.contracts.mailer.protocols import MailerProtocol
from lexigram.contracts.mailer.types import (
    Attachment,
    DeliveryState,
    EmailMessage,
    MessageAddress,
    MessageDeliveryReceipt,
    MessagePriority,
    MessageStatus,
)

__all__ = [
    "Attachment",
    "DeliveryState",
    "EmailMessage",
    "MailerError",
    "MailerProtocol",
    "MessageAddress",
    "MessageDeliveryReceipt",
    "MessagePriority",
    "MessageStatus",
]
