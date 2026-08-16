"""Composite WebhookBundleProvider wiring all webhook sub-providers."""

from __future__ import annotations

from lexigram.contracts.core.di import (
    BootContainerProtocol,
    ContainerRegistrarProtocol,
)
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.di.provider import Provider
from lexigram.webhook.config import WebhookConfig

__all__ = ["WebhookBundleProvider"]


class WebhookBundleProvider(Provider):
    """Bundle provider that orchestrates all webhook sub-providers.

    Composes core, delivery, verification, and admin providers into a
    single entry point for use in ``WebhookModule``.

    Args:
        config: Custom webhook configuration. Defaults to ``WebhookConfig()``.
    """

    config_key: str | None = "webhook"
    config_model = WebhookConfig

    def __init__(self, config: WebhookConfig | None = None) -> None:
        """Initialize with optional config override.

        Args:
            config: Custom webhook configuration. Defaults to ``WebhookConfig()``.
        """
        super().__init__(name="webhook_bundle", priority=ProviderPriority.COMMS)
        from lexigram.webhook.di.sub_providers.admin_provider import (
            WebhookAdminProvider,
        )
        from lexigram.webhook.di.sub_providers.core_provider import WebhookCoreProvider
        from lexigram.webhook.di.sub_providers.delivery_provider import (
            WebhookDeliveryProvider,
        )
        from lexigram.webhook.di.sub_providers.verification_provider import (
            WebhookVerificationProvider,
        )

        cfg = config or WebhookConfig()
        self._sub_providers: list[Provider] = [
            WebhookCoreProvider(config=cfg),
            WebhookDeliveryProvider(),
            WebhookVerificationProvider(),
        ]
        if cfg.enable_admin:
            self._sub_providers.append(WebhookAdminProvider())

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Delegate registration to all sub-providers.

        Args:
            container: DI container registrar.
        """
        for provider in self._sub_providers:
            await provider.register(container)

    async def boot(self, container: BootContainerProtocol) -> None:
        for provider in self._sub_providers:
            await provider.boot(container)

    async def shutdown(self) -> None:
        """Shut down all sub-providers in reverse order."""
        for provider in reversed(self._sub_providers):
            await provider.shutdown()
