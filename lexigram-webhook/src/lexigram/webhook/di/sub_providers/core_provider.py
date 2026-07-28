"""Core webhook DI provider: registers config, stores, and subscription service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.core.di import (
    BootContainerProtocol,
    ContainerRegistrarProtocol,
)
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.contracts.webhook.protocols import (
    WebhookDeliveryStoreProtocol,
    WebhookSubscriptionStoreProtocol,
)
from lexigram.di.provider import Provider

if TYPE_CHECKING:
    from lexigram.webhook.config import WebhookConfig

__all__ = ["WebhookCoreProvider"]


class WebhookCoreProvider(Provider):
    """Registers core webhook services: config, stores, and subscription service."""

    def __init__(self, config: WebhookConfig | None = None) -> None:
        """Initialize with optional config override.

        Args:
            config: Custom webhook config. Defaults to ``WebhookConfig()``.
        """
        super().__init__(name="webhook_core", priority=ProviderPriority.COMMS)
        self._config = config

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register webhook config, stores, and subscription service.

        Args:
            container: DI container registrar.
        """
        from lexigram.webhook.config import WebhookConfig
        from lexigram.webhook.store.memory import InMemoryWebhookStore
        from lexigram.webhook.subscription.service import WebhookSubscriptionService

        config = self._config or WebhookConfig()
        container.singleton(WebhookConfig, lambda: config)

        store = InMemoryWebhookStore()
        container.singleton(WebhookSubscriptionStoreProtocol, lambda: store)
        container.singleton(WebhookDeliveryStoreProtocol, lambda: store)
        container.singleton(WebhookSubscriptionService, WebhookSubscriptionService)

    async def boot(self, container: BootContainerProtocol) -> None:
        """Boot the core provider — no-op for memory backend.

        Args:
            container: DI container resolver.
        """
