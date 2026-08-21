"""Boot, shutdown, and health-check methods."""

from __future__ import annotations

import asyncio
import contextlib
import time
from typing import TYPE_CHECKING

from lexigram.concurrency.task_utils import create_tracked_task
from lexigram.contracts.core import (
    HealthCheckCategory,
    HealthCheckResult,
    HealthStatus,
    HookRegistryProtocol,
)
from lexigram.contracts.core.health import HealthCheckCategory
from lexigram.contracts.observability.metrics import (
    HealthCheckRegistryProtocol as _HealthCheckRegistry,
)
from lexigram.logging import get_logger
from lexigram.tasks.admin.contributor import TasksAdminContributor
from lexigram.tasks.execution.health import TaskHealth
from lexigram.tasks.execution.pool import WorkerPool
from lexigram.tasks.results.cache_backend import CacheBackendResultStore
from lexigram.tasks.scheduling.scheduler import TaskScheduler

if TYPE_CHECKING:

    from lexigram.contracts.core.di import (
        ContainerResolverProtocol,
    )

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Module-level helpers (no self; keep them small and testable)
# ---------------------------------------------------------------------------



class _TaskLifecycleMixin:
    """See TaskProvider."""
    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Start the task provider.

        Called by the framework on application startup after all registrations.
        """
        from lexigram.logging import LoggerProtocol as Logger

        # Resolve logger from container if available
        logger_instance = logger
        with contextlib.suppress(Exception):
            resolved = await container.resolve_optional(Logger)
            if resolved is not None:
                logger_instance = resolved

        self.logger = logger_instance.bind(provider="tasks")
        self.logger.info("Starting TaskProvider...")

        # Boot admin contributor
        contributor = await container.resolve(TasksAdminContributor)
        if contributor is not None:
            await contributor.on_admin_boot(container)

        hooks = await container.resolve_optional(HookRegistryProtocol)
        _wire_queue_hooks(self.queue, hooks)
        for _, queue in self._queue_services:
            _wire_queue_hooks(queue, hooks)

        # Multi-backend: connect all named queues in parallel before the rest of
        # the boot sequence.  Workers/scheduler always use self.queue (the primary).
        if self._queue_services:
            results = await asyncio.gather(
                *(_connect_queue(name, queue) for name, queue in self._queue_services),
                return_exceptions=True,
            )
            errors = [r for r in results if isinstance(r, BaseException)]
            if errors:
                # Roll back: close any queues that connected successfully.
                for _, queue in reversed(self._queue_services):
                    if hasattr(queue, "close"):
                        try:
                            await queue.close()
                        except Exception:  # noqa: BLE001, S110
                            pass
                raise errors[0]
            self.logger.info(
                "tasks_named_queues_connected",
                count=len(self._queue_services),
            )

        # Upgrade to CacheBackendResultStore if a CacheBackendProtocol is available.
        with contextlib.suppress(Exception):
            from lexigram.contracts.infra.cache import (
                CacheBackendProtocol as _CacheBackend,
            )

            cache_backend = await container.resolve(_CacheBackend)
            if cache_backend is not None:
                self._result_store = CacheBackendResultStore(cache_backend)
                self.logger.info(
                    "TaskProvider: using CacheBackendResultStore for distributed result persistence"
                )

        # Initialize worker pool - pass registry reference, not snapshot
        # This allows workers to pick up handlers registered after pool creation
        self.worker_pool = WorkerPool(
            self.queue,
            self.registry,
            self.worker_count,
            logger=self.logger,
            hooks=hooks,
            container=container,
            middleware_pipeline=self._middleware_pipeline,
        )
        await self.worker_pool.start()
        # Warn when running an in-memory queue outside of development/testing.
        from lexigram.tasks.backends.memory import MemoryTaskQueue

        if isinstance(self.queue, MemoryTaskQueue):
            env = "development"
            with contextlib.suppress(Exception):
                from lexigram.contracts.core.config import ConfigProtocol

                config = await container.resolve_optional(ConfigProtocol)
                if config is not None:
                    # Config object typically has .environment which is an Enum
                    env = getattr(config.environment, "value", str(config.environment))

            if env not in ("development", "test", "testing"):
                self.logger.warning(
                    "tasks_memory_queue_in_production",
                    note=(
                        "MemoryTaskQueue is volatile — all enqueued tasks will be lost "
                        "on process restart. Use RedisTaskQueue or RabbitMQTaskQueue "
                        "in production deployments."
                    ),
                    env=env,
                )

        # Initialize scheduler if enabled
        if self.enable_scheduler:
            self.scheduler = TaskScheduler()
            self.scheduler_task = create_tracked_task(
                self.scheduler.start_scheduler(self._enqueue_job),
                self._background_tasks,
                name="task_provider_scheduler",
            )

        self.logger.info("TaskProvider started with %d workers", self.worker_count)

        # Register task health check with the kernel's HealthChecker if available.
        # This is a best-effort registration; a missing HealthChecker just means
        # health information is not surfaced through the kernel's aggregated endpoint.
        with contextlib.suppress(Exception):
            health_checker = await container.resolve(_HealthCheckRegistry)
            health_checker.add(
                "tasks",
                self.health_check,
                category=HealthCheckCategory.READINESS,
            )
            self.logger.debug("Registered task health check with kernel HealthChecker")

    async def shutdown(self) -> None:
        """Shutdown the task provider gracefully"""
        if hasattr(self, "logger"):
            self.logger.info("Shutting down TaskProvider...")
        else:
            logger.info("Shutting down TaskProvider...")

        # Stop scheduler
        if self.scheduler_task:
            if self.scheduler:
                await self.scheduler.stop_scheduler()
            self.scheduler_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.scheduler_task

        # Stop worker pool
        if self.worker_pool:
            await self.worker_pool.stop()

        # Close named queues LIFO (multi-backend mode).
        if self._queue_services:
            for _, queue in reversed(self._queue_services):
                if hasattr(queue, "close"):
                    try:
                        await queue.close()
                    except Exception:  # noqa: BLE001, S110
                        pass

        # Close primary queue (always — single-backend and multi-backend both use it
        # for workers/scheduler).
        await self.queue.close()

        if hasattr(self, "logger"):
            self.logger.info("TaskProvider shutdown complete")
        else:
            logger.info("TaskProvider shutdown complete")

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check task provider health.

        In multi-backend mode the overall status is the worst individual status
        across all named queues.  ``TaskQueueProtocol`` does not expose a
        ``health_check()`` method, so liveness is probed via ``get_task_count()``.

        Returns:
            HealthCheckResult with current status and metrics.
        """
        if self._queue_services:
            results = await asyncio.gather(
                *(_check_queue_health(queue) for _, queue in self._queue_services),
                return_exceptions=True,
            )
            worst = HealthStatus.HEALTHY
            for r in results:
                if isinstance(r, BaseException) or r.status == HealthStatus.UNHEALTHY:
                    worst = HealthStatus.UNHEALTHY
                elif (
                    r.status == HealthStatus.DEGRADED
                    and worst != HealthStatus.UNHEALTHY
                ):
                    worst = HealthStatus.DEGRADED
            return HealthCheckResult(
                component=self.name,
                status=worst,
                duration_ms=0.0,
                category=HealthCheckCategory.READINESS,
            )

        # ------------------------------------------------------------------ #
        # Single-backend path (original behaviour, preserved exactly)         #
        # ------------------------------------------------------------------ #
        try:
            queue_size = await self.queue.get_task_count()

            health_data = TaskHealth(
                status="healthy",
                message="Task provider is operational",
                timestamp=time.time(),
                queue_size=queue_size,
                worker_count=self.worker_count,
                scheduler_enabled=self.enable_scheduler,
            )

            # Add worker pool stats if available
            if self.worker_pool:
                pool_stats = self.worker_pool.get_pool_stats()
                health_data.active_workers = pool_stats["active_workers"]
                health_data.total_jobs_processed = pool_stats["total_jobs_processed"]
                health_data.total_jobs_succeeded = pool_stats["total_jobs_succeeded"]
                health_data.total_jobs_failed = pool_stats["total_jobs_failed"]
                health_data.details["pool_stats"] = pool_stats

            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.HEALTHY,
                details=health_data.to_dict(),
                category=HealthCheckCategory.READINESS,
            )

        except Exception as e:
            # Intentionally broad: health checks should report failure rather than raising.
            logger.exception("TaskProvider health check failed")
            health_data = TaskHealth(status="unhealthy", message=str(e))
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                error=str(e),
                details=health_data.to_dict(),
                category=HealthCheckCategory.READINESS,
            )


async def _connect_queue(name: str, queue: Any) -> None:  # noqa: RUF029
    """Connect a single named queue if it exposes a ``connect()`` method."""
    if hasattr(queue, "connect"):
        await queue.connect()


def _wire_queue_hooks(queue: Any, hooks: HookRegistryProtocol | None) -> None:
    """Attach an optional hook registry to a queue when supported."""
    if hasattr(queue, "set_hook_registry"):
        queue.set_hook_registry(hooks)


async def _check_queue_health(queue: Any) -> HealthCheckResult:
    """Probe a queue by calling ``get_task_count()`` (cheapest round-trip).

    ``TaskQueueProtocol`` does not define a ``health_check()`` method so we
    use ``get_task_count()`` as the liveness indicator.
    """
    try:
        await queue.get_task_count()
        return HealthCheckResult(component="tasks", status=HealthStatus.HEALTHY)
    except Exception as exc:  # noqa: BLE001
        return HealthCheckResult(
            component="tasks",
            status=HealthStatus.UNHEALTHY,
            error=str(exc),
        )


