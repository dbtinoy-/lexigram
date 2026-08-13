"""Package-internal types for lexigram-webhook.

Shared types (``WebhookSubscription``, ``WebhookEvent``, ``DeliveryAttempt``,
``DeliveryStatus``) live in ``lexigram.contracts.webhook.types``. This module
defines types internal to the webhook package implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

__all__ = [
    "DeliveryBatch",
    "RetrySchedule",
    "WebhookStoreBackend",
]


class WebhookStoreBackend(StrEnum):
    """Supported webhook store backends."""

    MEMORY = "memory"
    SQL = "sql"


@dataclass(frozen=True)
class RetrySchedule:
    """Computed retry schedule for a failed delivery.

    Attributes:
        attempt_number: The next attempt number (1-based).
        delay_seconds: Seconds to wait before this retry.
        is_final: True if this is the last retry before dead-letter.
    """

    attempt_number: int
    delay_seconds: float
    is_final: bool = False


@dataclass(frozen=True)
class DeliveryBatch:
    """A batch of subscriptions to deliver a single event to.

    Attributes:
        event_id: The event being delivered.
        event_type: Event type string.
        subscription_ids: List of target subscription IDs.
        scheduled_at: When this batch was created.
    """

    event_id: str
    event_type: str
    subscription_ids: list[str] = field(default_factory=list)
    scheduled_at: datetime | None = None
