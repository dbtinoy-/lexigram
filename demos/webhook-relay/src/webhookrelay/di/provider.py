"""Lifecycle wiring for the webhook ingress and relay demo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.core.health import (
    HealthCheckCategory,
    HealthCheckResult,
    HealthStatus,
)
from lexigram.di.provider import Provider
from lexigram.webhook.subscription.service import WebhookSubscriptionService
from lexigram.webhook.verification.hmac import HMACSignatureVerifier
from webhookrelay.config import WebhookRelayConfig
from webhookrelay.controllers.api import WebhookApiController

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

__all__ = ["WebhookRelayProvider"]


class WebhookRelayProvider(Provider):
    """Bind the demo's event ledger to Lexigram webhook services.

    ``WebhookModule`` provides the subscription store/service and the
    constant-time HMAC verifier. This provider only owns the browser-friendly
    relay ledger and the composition of the demo controller.
    """

    name = "webhookrelay"
    config_key: str | None = "webhookrelay"
    config_model: type | None = WebhookRelayConfig

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Declare config and controller bindings."""
        cfg = self.config or WebhookRelayConfig()
        container.singleton(WebhookRelayConfig, instance=cfg)
        container.singleton(WebhookApiController, WebhookApiController)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Resolve Lexigram webhook capabilities and wire the controller."""
        from webhookrelay.services.relay import WebhookRelay

        cfg = await container.resolve(WebhookRelayConfig)
        verifier = await container.resolve(HMACSignatureVerifier)
        subscriptions = await container.resolve(WebhookSubscriptionService)
        relay = WebhookRelay()

        container.bind(
            WebhookApiController,
            WebhookApiController(
                relay=relay,
                verifier=verifier,
                secret=cfg.secret_key,
                max_payload_size=cfg.max_payload_size,
                subscriptions=subscriptions,
            ),
        )

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report readiness of the relay controller."""
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            category=HealthCheckCategory.READINESS,
        )
