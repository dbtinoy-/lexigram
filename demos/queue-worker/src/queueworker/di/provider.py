"""Lifecycle wiring for the focused Lexigram queue-worker demo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.core.health import (
    HealthCheckCategory,
    HealthCheckResult,
    HealthStatus,
)
from lexigram.contracts.queue.protocols import QueueProtocol
from lexigram.di.provider import Provider
from queueworker.config import QueueWorkerConfig
from queueworker.controllers.api import QueueApiController
from queueworker.services.processor import MessageProcessor

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

__all__ = ["QueueWorkerProvider"]


class QueueWorkerProvider(Provider):
    """Bind one Lexigram MessageConsumer to the configured task topic."""

    name = "queueworker"
    config_key: str | None = "queueworker"
    config_model: type | None = QueueWorkerConfig

    def __init__(self) -> None:
        super().__init__()
        self._queue: QueueProtocol | None = None
        self._processor: MessageProcessor | None = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Declare config and controller bindings."""
        cfg = self.config or QueueWorkerConfig()
        container.singleton(QueueWorkerConfig, instance=cfg)
        container.singleton(QueueApiController, QueueApiController)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Resolve QueueProtocol, subscribe the consumer, then wire HTTP."""
        cfg = await container.resolve(QueueWorkerConfig)
        queue = await container.resolve(QueueProtocol)
        processor = MessageProcessor(queue=queue, topic=cfg.queue_name)
        await processor.start()

        self._queue = queue
        self._processor = processor
        container.bind(
            QueueApiController,
            QueueApiController(
                queue=queue,
                processor=processor,
                max_retries=cfg.max_retries,
            ),
        )

    async def shutdown(self) -> None:
        """Stop the consumer before closing the Lexigram queue backend."""
        if self._processor is not None:
            await self._processor.stop()
        if self._queue is not None and hasattr(self._queue, "close"):
            await self._queue.close()  # type: ignore[attr-defined]

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report readiness of the queue worker."""
        ready = self._processor is not None and self._processor.is_running()
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY if ready else HealthStatus.UNHEALTHY,
            category=HealthCheckCategory.READINESS,
        )
