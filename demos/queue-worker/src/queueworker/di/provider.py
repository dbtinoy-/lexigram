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
    """Bind the queue worker services as container-managed singletons."""

    name = "queueworker"

    config_key: str | None = "queueworker"
    config_model: type | None = QueueWorkerConfig

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Declare bindings; concrete wiring happens in :meth:`boot`."""
        cfg = self.config or QueueWorkerConfig()

        container.singleton(QueueWorkerConfig, instance=cfg)

        # Class bindings so the keys exist; boot() replaces them with
        # fully-wired instances via container.bind().
        container.singleton(QueueApiController, QueueApiController)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Resolve cross-module dependencies and bind concrete instances."""
        from queueworker.queue import InMemoryQueue
        from queueworker.services.processor import MessageProcessor

        cfg = await container.resolve(QueueWorkerConfig)

        # Create the queue and processor
        queue = InMemoryQueue()
        processor = MessageProcessor(queue=queue)

        # Bind the wired controller
        container.bind(
            QueueApiController,
            QueueApiController(queue=queue, processor=processor),
        )

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report readiness of the queue worker."""
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            category=HealthCheckCategory.READINESS,
        )
