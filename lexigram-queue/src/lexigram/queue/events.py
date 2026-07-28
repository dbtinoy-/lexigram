"""Domain events for queue operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from lexigram.contracts.domain.events import DomainEvent


@dataclass(frozen=True, init=False)
class MessageConsumedEvent(DomainEvent):
    """Message was successfully consumed from the queue.

    Consumed by: message tracking, audit logging, metrics collection.
    """

    message_id: str = field(kw_only=True)
    queue_name: str = field(kw_only=True)
    consumer_id: str = field(kw_only=True)
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(UTC), kw_only=True
    )


@dataclass(frozen=True, init=False)
class MessageDeadLetteredEvent(DomainEvent):
    """Message failed and was moved to dead-letter queue.

    Consumed by: error handling, retry management, incident tracking.
    """

    message_id: str = field(kw_only=True)
    queue_name: str = field(kw_only=True)
    reason: str = field(kw_only=True)
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(UTC), kw_only=True
    )


@dataclass(frozen=True, init=False)
class ConsumerRegisteredEvent(DomainEvent):
    """Consumer was registered to a queue.

    Consumed by: consumer tracking, lifecycle management, monitoring.
    """

    consumer_id: str = field(kw_only=True)
    queue_name: str = field(kw_only=True)
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(UTC), kw_only=True
    )
