"""Provider wiring for the queue worker demo.

Convention followed: **Provider pattern** — ``QueueWorkerProvider`` is the
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
from queueworker.config import QueueWorkerConfig
from queueworker.controllers.api import QueueApiController

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

__all__ = ["QueueWorkerProvider"]


class QueueWorkerProvider(Provider):
    """Bind the queue worker services as container-managed singletons.

    This provider demonstrates the full lifecycle:
    - ``register()`` declares the config and controller bindings
    - ``boot()`` creates the in-memory queue and wires the controller
    - ``health_check()`` reports readiness status
    """

    name = "queueworker"

    # Config binding — the framework injects the typed YAML section here
    config_key: str | None = "queueworker"
    config_model: type | None = QueueWorkerConfig

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Declare bindings; concrete wiring happens in :meth:`boot`.

        This method runs AFTER the framework has loaded the config.
        ``self.config`` contains the typed ``QueueWorkerConfig`` instance
        with YAML values + env overrides already merged.
        """
        cfg = self.config or QueueWorkerConfig()

        # Bind the config as a singleton — other services can resolve it
        container.singleton(QueueWorkerConfig, instance=cfg)

        # Class bindings so the keys exist; boot() replaces them with
        # fully-wired instances via container.bind().
        container.singleton(QueueApiController, QueueApiController)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Resolve cross-module dependencies and bind concrete instances.

        This method runs AFTER all providers have registered.
        Resolution is safe — all bindings are in place.
        """
        from queueworker.queue import InMemoryQueue
        from queueworker.services.processor import MessageProcessor

        cfg = await container.resolve(QueueWorkerConfig)

        # Create the queue and processor
        # In production, replace with lexigram-queue's backend:
        #   from lexigram_queue import RabbitMQBackend
        #   queue = RabbitMQBackend(config=cfg)
        queue = InMemoryQueue()
        processor = MessageProcessor(queue=queue)

        # Bind the wired controller — the router resolves this for
        # every request, so per-request resolution reuses the same instance.
        container.bind(
            QueueApiController,
            QueueApiController(queue=queue, processor=processor),
        )

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report readiness of the queue worker.

        Called by the framework's health check system.  Return
        HEALTHY if the service is ready to handle requests.
        """
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            category=HealthCheckCategory.READINESS,
        )
