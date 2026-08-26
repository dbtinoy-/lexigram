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
        config: Custom webhook configuration. When ``None``, the
            orchestrator injects the typed ``webhook`` yaml section after
            construction and sub-providers are composed in :meth:`register`.
    """

    config_key: str | None = "webhook"
    config_model = WebhookConfig

    def __init__(self, config: WebhookConfig | None = None) -> None:
        """Initialize with optional config override.

        Args:
            config: Custom webhook configuration. Defaults to
                ``WebhookConfig()`` when no yaml section is injected either.
        """
        super().__init__(name="webhook_bundle", priority=ProviderPriority.COMMS)
        self.config = config
        self._sub_providers: list[Provider] = []
        if config is not None:
            # Explicit config: compose eagerly. Zero-config construction
            # defers to register(), after the orchestrator has injected
            # the yaml section.
            self._compose_sub_providers()

    def _compose_sub_providers(self) -> None:
        """(Re)build sub-providers from the current ``self.config``.

        Called from ``__init__`` (explicit config) and lazily from
        ``register()`` when the orchestrator injected the yaml section
        after construction. Recomposition before any ``register()`` call
        is safe — nothing has been registered yet.
        """
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

        cfg = self.config
        self._sub_providers = [
            WebhookCoreProvider(config=cfg),
            WebhookDeliveryProvider(),
            WebhookVerificationProvider(),
        ]
        if cfg is None or cfg.enable_admin:
            self._sub_providers.append(WebhookAdminProvider())

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Delegate registration to all sub-providers.

        Late config binding: the orchestrator injects the typed ``webhook``
        section (via ``config_key``) after construction and before this
        call. If ``configure()`` ran with no explicit config, compose now so
        the automatic path behaves identically to the explicit one.

        Args:
            container: DI container registrar.
        """
        if not self._sub_providers:
            self._compose_sub_providers()
        for provider in self._sub_providers:
            await provider.register(container)

    async def boot(self, container: BootContainerProtocol) -> None:
        for provider in self._sub_providers:
            await provider.boot(container)

    async def shutdown(self) -> None:
        """Shut down all sub-providers in reverse order."""
        for provider in reversed(self._sub_providers):
            await provider.shutdown()
