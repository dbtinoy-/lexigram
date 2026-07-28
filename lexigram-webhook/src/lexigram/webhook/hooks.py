"""Root hook payload surface for lexigram-webhook.

Defines canonical payload dataclasses for webhook lifecycle hook points.
Actual hook registration and invocation use the framework's string-keyed
``HookRegistryProtocol`` action/filter APIs.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "WebhookBeforeDeliveryHook",
    "WebhookDeliveryCompletedHook",
    "WebhookSubscriptionChangedHook",
]


@dataclass(frozen=True, kw_only=True)
class WebhookBeforeDeliveryHook:
    """Payload fired before a webhook delivery attempt is made.

    Attributes:
        subscription_id: Target subscription identifier.
        event_type: Event type about to be delivered.
        url: Destination URL.
    """

    subscription_id: str
    event_type: str
    url: str


@dataclass(frozen=True, kw_only=True)
class WebhookDeliveryCompletedHook:
    """Payload fired after a webhook delivery attempt completes.

    Attributes:
        attempt_id: Unique identifier of the completed attempt.
        subscription_id: Target subscription.
        status: Delivery status string (e.g. ``"delivered"``, ``"failed"``).
        status_code: HTTP response status code, or None if connection failed.
    """

    attempt_id: str
    subscription_id: str
    status: str
    status_code: int | None = None


@dataclass(frozen=True, kw_only=True)
class WebhookSubscriptionChangedHook:
    """Payload fired when a subscription is created, updated, or deleted.

    Attributes:
        subscription_id: The affected subscription.
        change_type: One of ``"created"``, ``"updated"``, ``"deleted"``.
    """

    subscription_id: str
    change_type: str
