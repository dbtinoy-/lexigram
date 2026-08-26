"""WebhookModule — IoC module for the Lexigram webhook subsystem."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from lexigram.contracts.webhook.protocols import (
    WebhookDeliveryServiceProtocol,
    WebhookSubscriptionStoreProtocol,
)
from lexigram.di.module import DynamicModule, module
from lexigram.webhook.subscription.service import WebhookSubscriptionService

if TYPE_CHECKING:
    from lexigram.webhook.config import WebhookConfig

__all__ = ["WebhookModule"]


@module()
class WebhookModule(str, Enum):
    """Lexigram webhook management module.

    Provides subscription CRUD, delivery pipeline, HMAC signature
    verification, and dead-letter queue management.

    Usage::

        app.use(WebhookModule.configure())
        app.use(WebhookModule.configure(WebhookConfig(store_backend="sql")))
    """

    @classmethod
    def configure(cls, config: WebhookConfig | None = None) -> DynamicModule:
        """Configure the webhook module with optional settings.

        Args:
            config: Custom webhook configuration. When ``None``, the
                orchestrator injects the ``webhook`` yaml section into the
                bundle provider before registration (falling back to
                ``WebhookConfig()`` defaults when no section exists).

        Returns:
            DynamicModule ready for registration with the app container.
        """
        from lexigram.webhook.di.bundle_provider import WebhookBundleProvider

        return DynamicModule(
            module=cls,
            providers=[WebhookBundleProvider(config=config)],
            exports=[
                WebhookSubscriptionStoreProtocol,
                WebhookDeliveryServiceProtocol,
                WebhookSubscriptionService,
            ],
        )
