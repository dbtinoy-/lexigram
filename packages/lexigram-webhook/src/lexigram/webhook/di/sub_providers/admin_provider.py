"""Admin DI provider: registers the webhook admin dashboard contributor."""

from __future__ import annotations

from lexigram.contracts.core.di import (
    BootContainerProtocol,
    ContainerRegistrarProtocol,
)
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.di.provider import Provider

__all__ = ["WebhookAdminProvider"]


class WebhookAdminProvider(Provider):
    """Registers the webhook admin dashboard contributor."""

    def __init__(self) -> None:
        """Initialize the admin provider."""
        super().__init__(name="webhook_admin", priority=ProviderPriority.LOW)

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register the admin contributor.

        Args:
            container: DI container registrar.
        """
        from lexigram.webhook.admin.contributor import WebhookAdminContributor

        container.singleton(WebhookAdminContributor)

    async def boot(self, container: BootContainerProtocol) -> None:
        """Boot the admin provider.

        Args:
            container: DI container resolver.
        """
