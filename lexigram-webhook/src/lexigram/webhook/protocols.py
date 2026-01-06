"""Public protocol surface for ``lexigram.webhook``.

Re-exports the canonical webhook protocols from ``lexigram-contracts`` so
consumers can import from ``lexigram.webhook`` directly.
"""

from __future__ import annotations

from lexigram.contracts.webhook import (
    WebhookDeliveryServiceProtocol,
    WebhookDeliveryStoreProtocol,
    WebhookSubscriptionStoreProtocol,
)

__all__ = [
    "WebhookDeliveryServiceProtocol",
    "WebhookDeliveryStoreProtocol",
    "WebhookSubscriptionStoreProtocol",
]
