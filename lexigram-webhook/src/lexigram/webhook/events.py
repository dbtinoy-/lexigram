"""Root event surface for lexigram-webhook.

Defines domain events emitted by the webhook delivery pipeline.
Consumers subscribe via
:class:`~lexigram.contracts.events.protocols.EventBusProtocol`.
"""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.contracts.domain.events import DomainEvent

__all__ = [
    "WebhookDeliveredEvent",
    "WebhookDeliveryFailedEvent",
    "WebhookSubscriptionCreatedEvent",
]


@dataclass(frozen=True, kw_only=True)
class WebhookSubscriptionCreatedEvent(DomainEvent):
    """Emitted when a new webhook subscription is registered.

    Attributes:
        subscription_id: Unique identifier of the new subscription.
        url: The registered endpoint URL.
    """

    subscription_id: str
    url: str


@dataclass(frozen=True, kw_only=True)
class WebhookDeliveredEvent(DomainEvent):
    """Emitted when a webhook event is successfully delivered.

    Attributes:
        attempt_id: Unique identifier of the delivery attempt.
        subscription_id: Target subscription.
        event_type: Event type that was delivered.
    """

    attempt_id: str
    subscription_id: str
    event_type: str


@dataclass(frozen=True, kw_only=True)
class WebhookDeliveryFailedEvent(DomainEvent):
    """Emitted when a webhook delivery attempt fails.

    Attributes:
        attempt_id: Unique identifier of the delivery attempt.
        subscription_id: Target subscription.
        event_type: Event type that failed delivery.
        error: Human-readable error description.
        attempt_number: The attempt number that failed.
    """

    attempt_id: str
    subscription_id: str
    event_type: str
    error: str
    attempt_number: int = 1
