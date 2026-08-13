"""Event bus → webhook bridge."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.logging.factory import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.webhook.protocols import WebhookDeliveryServiceProtocol
    from lexigram.contracts.webhook.types import WebhookEvent

logger = get_logger(__name__)

__all__ = ["EventBusWebhookBridge"]


class EventBusWebhookBridge:
    """Bridges framework domain events to the webhook delivery system.

    Subscribes to the event bus and forwards matching events to the
    webhook delivery service as WebhookEvents.
    """

    def __init__(
        self,
        delivery_service: WebhookDeliveryServiceProtocol,
    ) -> None:
        """Initialize the bridge.

        Args:
            delivery_service: Webhook delivery service for dispatching.
        """
        self._delivery_service = delivery_service

    async def forward(self, event: WebhookEvent) -> None:
        """Forward a domain event to the webhook delivery system.

        Args:
            event: Prepared WebhookEvent to dispatch.
        """
        logger.debug(
            "webhook_bridge_forwarding",
            event_type=event.event_type,
            event_id=event.event_id,
        )
        await self._delivery_service.dispatch(event)
