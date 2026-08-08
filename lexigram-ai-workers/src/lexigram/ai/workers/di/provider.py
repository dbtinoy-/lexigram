"""Workers DI provider — registers background workers with the container."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from lexigram.ai.workers.batch_embedding.worker import BatchEmbeddingWorker
from lexigram.ai.workers.config import WorkersConfig
from lexigram.ai.workers.dlq.worker import DeadLetterQueueWorker
from lexigram.ai.workers.document_ingestion.worker import DocumentIngestionWorker
from lexigram.ai.workers.maintenance.worker import MaintenanceWorker
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.di.provider import Provider
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

logger = get_logger(__name__)

# Worker types managed by this provider
_WORKER_TYPES: tuple[type, ...] = (
    BatchEmbeddingWorker,
    DocumentIngestionWorker,
    MaintenanceWorker,
    DeadLetterQueueWorker,
)


class WorkersProvider(Provider):
    """Provider for AI background workers.

    Reads :class:`~lexigram.ai.workers.config.WorkersConfig` and registers
    workers for batch embedding, ingestion, maintenance, and DLQ handling.

    Lifecycle:
        - ``register`` — binds worker singletons into the container.
        - ``boot`` — resolves workers and starts each as a background async task.
        - ``shutdown`` — calls ``stop()`` on every worker, then awaits each
          background task to ensure graceful queue draining.
    """

    name = "workers"
    priority = ProviderPriority.INFRASTRUCTURE

    def __init__(
        self,
        config: WorkersConfig | None = None,
        enable_scheduler: bool = True,
    ) -> None:
        super().__init__()
        self._config = config or WorkersConfig()
        self._enable_scheduler = enable_scheduler
        self._workers: list[Any] = []
        self._tasks: set[asyncio.Task[None]] = set()

    @classmethod
    def from_config(cls, config: WorkersConfig, **context) -> WorkersProvider:
        """Factory method for DI container setup."""
        return cls(config)

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register workers with the DI container."""
        container.singleton(WorkersConfig, self._config)

        if not self._config.enabled:
            logger.info(
                "workers_provider_disabled", reason="WorkersConfig.enabled=False"
            )
            return

        for worker_type in _WORKER_TYPES:
            if hasattr(container, "register"):
                container.register(worker_type)
            else:
                container.transient(worker_type, worker_type)

        logger.info("workers_provider_registered", worker_count=len(_WORKER_TYPES))

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Resolve workers from the container and start each as a background task.

        Each worker's ``start()`` coroutine is wrapped in an ``asyncio.Task``
        so it runs concurrently. Task references are stored in ``_tasks`` to
        prevent garbage collection (Ruff RUF006).

        Args:
            container: Container resolver for resolving worker instances.
        """
        if not self._config.enabled:
            logger.debug("workers_provider_boot_skipped", reason="disabled")
            return

        for worker_type in _WORKER_TYPES:
            try:
                worker: Any = await container.resolve(worker_type)
            except (
                LookupError,
                RuntimeError,
                TypeError,
                ValueError,
                AttributeError,
            ) as exc:
                logger.warning(
                    "worker_resolve_failed",
                    worker=worker_type.__name__,
                    error=str(exc),
                )
                continue

            self._workers.append(worker)
            task = asyncio.create_task(
                worker.start(),
                name=f"worker.{worker_type.__name__}",
            )
            self._tasks.add(task)
            task.add_done_callback(self._on_worker_done)
            logger.info("worker_started", worker=worker_type.__name__)

        logger.info("workers_provider_booted", workers_started=len(self._workers))

    async def shutdown(self) -> None:
        """Stop all workers gracefully and await their background tasks.

        Calls ``stop()`` on every worker in reverse start order, then waits
        for each background task to finish (with a 30 s timeout per task).
        """
        for worker in reversed(self._workers):
            try:
                await worker.stop()
            except (OSError, RuntimeError) as exc:
                logger.warning(
                    "worker_stop_error",
                    worker=type(worker).__name__,
                    error=str(exc),
                )

        if self._tasks:
            await asyncio.wait(self._tasks, timeout=30.0)
            pending = {t for t in self._tasks if not t.done()}
            for task in pending:
                task.cancel()
                logger.warning("worker_task_cancelled", task=task.get_name())

        self._workers.clear()
        self._tasks.clear()
        logger.info("workers_provider_shutdown")

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Health check — always healthy (in-process domain provider).

        No external backend to ping.

        Args:
            timeout: Ignored for in-process providers.

        Returns:
            Always HEALTHY — no external backend to ping.
        """
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            details={"status": "operational"},
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _on_worker_done(self, task: asyncio.Task[None]) -> None:
        """Callback to handle completed or failed worker tasks."""
        self._tasks.discard(task)
        if task.cancelled():
            logger.info("worker_task_cancelled", task=task.get_name())
        elif exc := task.exception():
            logger.error(
                "worker_task_failed",
                task=task.get_name(),
                error=str(exc),
            )


__all__ = ["WorkersProvider"]
