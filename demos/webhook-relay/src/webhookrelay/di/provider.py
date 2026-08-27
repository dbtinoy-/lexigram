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

Lifecycle:
  1. ``register()`` — declare bindings (no resolution)
  2. ``boot()`` — resolve cross-module deps, create instances, bind
  3. ``shutdown()`` — cleanup (not needed for in-memory stores)

For full reference see:
- ``lexigram.di.provider.Provider`` — base provider class
- ``lexigram.contracts.core.di`` — container protocols
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
    """Bind the webhook relay services as container-managed singletons.

    This provider demonstrates the full lifecycle:
    - ``register()`` declares the config and controller bindings
    - ``boot()`` creates the signer, validator, and relay
    - ``health_check()`` reports readiness status
    """

    name = "webhookrelay"

    # Config binding — the framework injects the typed YAML section here
    config_key: str | None = "webhookrelay"
    config_model: type | None = WebhookRelayConfig

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Declare bindings; concrete wiring happens in :meth:`boot`.

        This method runs AFTER the framework has loaded the config.
        ``self.config`` contains the typed ``WebhookRelayConfig`` instance
        with YAML values + env overrides already merged.
        """
        cfg = self.config or WebhookRelayConfig()

        # Bind the config as a singleton — other services can resolve it
        container.singleton(WebhookRelayConfig, instance=cfg)

        # Class bindings so the keys exist; boot() replaces them with
        # fully-wired instances via container.bind().
        container.singleton(WebhookApiController, WebhookApiController)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Resolve cross-module dependencies and bind concrete instances.

        This method runs AFTER all providers have registered.
        Resolution is safe — all bindings are in place.
        """
        from webhookrelay.services.relay import WebhookRelay
        from webhookrelay.services.validator import WebhookValidator
        from webhookrelay.signer import HmacSigner

        cfg = await container.resolve(WebhookRelayConfig)

        # Create the signer
        # In production, use a secure secret management system:
        #   secret = await vault.get_secret("webhook/hmac")
        signer = HmacSigner(secret=cfg.secret_key)

        # Create the validator and relay
        validator = WebhookValidator(
            signer=signer, max_payload_size=cfg.max_payload_size
        )
        relay = WebhookRelay()

        # Bind the wired controller — the router resolves this for
        # every request, so per-request resolution reuses the same instance.
        container.bind(
            WebhookApiController,
            WebhookApiController(validator=validator, relay=relay),
        )

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report readiness of the webhook relay.

        Called by the framework's health check system.  Return
        HEALTHY if the service is ready to handle requests.
        """
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            category=HealthCheckCategory.READINESS,
        )
