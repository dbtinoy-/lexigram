"""Provider wiring for the webhook relay demo.

Convention followed: **Provider pattern** — ``WebhookRelayProvider`` is the
canonical shape (mirrors ``lexigram-auth`` + the boot-phase ``bind()``
contract in ``lexigram.contracts.core.di``):

- ``register()`` only *declares* bindings.  Zero-arg factories cover
  purely config-derived services; dependency-full services are declared
  as class bindings and instantiated in :meth:`boot`.
- ``boot()`` resolves cross-module dependencies after every provider
  has registered and rebinds the concrete instances via
  ``container.bind()``.
- Controllers are constructed by the router from the container; ``boot``
  binds their prebuilt instances so per-request resolution reuses them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.core.health import (
    HealthCheckCategory,
    HealthCheckResult,
    HealthStatus,
)
from lexigram.di.provider import Provider
from webhookrelay.config import WebhookRelayConfig
from webhookrelay.controllers.api import WebhookApiController

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

__all__ = ["WebhookRelayProvider"]


class WebhookRelayProvider(Provider):
    """Bind the webhook relay services as container-managed singletons."""

    name = "webhookrelay"

    config_key: str | None = "webhookrelay"
    config_model: type | None = WebhookRelayConfig

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Declare bindings; concrete wiring happens in :meth:`boot`."""
        cfg = self.config or WebhookRelayConfig()

        container.singleton(WebhookRelayConfig, instance=cfg)

        # Class bindings so the keys exist; boot() replaces them with
        # fully-wired instances via container.bind().
        container.singleton(WebhookApiController, WebhookApiController)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Resolve cross-module dependencies and bind concrete instances."""
        from webhookrelay.services.relay import WebhookRelay
        from webhookrelay.services.validator import WebhookValidator
        from webhookrelay.signer import HmacSigner

        cfg = await container.resolve(WebhookRelayConfig)

        # Create the signer
        signer = HmacSigner(secret=cfg.secret_key)

        # Create the validator and relay
        validator = WebhookValidator(signer=signer, max_payload_size=cfg.max_payload_size)
        relay = WebhookRelay()

        # Bind the wired controller
        container.bind(
            WebhookApiController,
            WebhookApiController(validator=validator, relay=relay),
        )

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report readiness of the webhook relay."""
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            category=HealthCheckCategory.READINESS,
        )
