"""Delivery DI provider: registers sender, delivery service, and dead-letter manager."""

from __future__ import annotations

from lexigram.contracts.core.di import (
    BootContainerProtocol,
    ContainerRegistrarProtocol,
)
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.contracts.webhook.protocols import WebhookDeliveryServiceProtocol
from lexigram.di.provider import Provider

__all__ = ["WebhookDeliveryProvider"]


class WebhookDeliveryProvider(Provider):
    """Registers webhook delivery pipeline services."""

    def __init__(self) -> None:
        """Initialize the delivery provider."""
        super().__init__(name="webhook_delivery", priority=ProviderPriority.COMMS)

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register sender, delivery service, and dead-letter manager.

        Args:
            container: DI container registrar.
        """
        from lexigram.webhook.delivery.dead_letter import DeadLetterManager
        from lexigram.webhook.delivery.sender import WebhookSender
        from lexigram.webhook.delivery.service import WebhookDeliveryService

        container.singleton(WebhookSender, WebhookSender)
        container.singleton(WebhookDeliveryServiceProtocol, WebhookDeliveryService)
        container.singleton(DeadLetterManager, DeadLetterManager)

    async def boot(self, container: BootContainerProtocol) -> None:
        """Boot the delivery provider.

        Args:
            container: DI container resolver.
        """
