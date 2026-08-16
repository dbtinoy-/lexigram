"""Task provider for Lexigram Framework integration

This module provides the TaskProvider for DI container integration.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from typing import TYPE_CHECKING, Any, cast

from lexigram.concurrency.task_utils import create_tracked_task
from lexigram.contracts.admin.protocols import AdminContributorProtocol
from lexigram.contracts.core import (
    HealthCheckCategory,
    HealthCheckResult,
    HealthStatus,
    HookRegistryProtocol,
    ProviderPriority,
)
from lexigram.contracts.core.health import HealthCheckCategory
from lexigram.contracts.core.idempotency import IdempotencyStoreProtocol
from lexigram.contracts.infra.tasks import (
    IdempotencyManagerProtocol,
    IdempotentTaskManagerProtocol,
    TaskExecutorProtocol,
    TaskQueueProtocol,
)
from lexigram.contracts.observability.metrics import (
    HealthCheckRegistryProtocol as _HealthCheckRegistry,
)
from lexigram.di.provider import Provider
from lexigram.logging import get_logger
from lexigram.tasks.admin.contributor import TasksAdminContributor
from lexigram.tasks.admin.handlers.avg_duration import AvgDurationWidgetHandler
from lexigram.tasks.admin.handlers.tasks_summary import TasksSummaryWidgetHandler
from lexigram.tasks.backends.registry import TaskBackendRegistry
from lexigram.tasks.config import TaskConfig
from lexigram.tasks.exceptions import TaskRegistrationError
from lexigram.tasks.execution.health import TaskHealth
from lexigram.tasks.execution.manager import (
    IdempotencyManager,
    IdempotentTaskManager,
)
from lexigram.tasks.execution.metrics import TaskMetricsCollector
from lexigram.tasks.execution.pool import WorkerPool
from lexigram.tasks.execution.registry import HandlerRegistry
from lexigram.tasks.middleware.core import TaskMiddlewarePipeline
from lexigram.tasks.results.cache_backend import CacheBackendResultStore
from lexigram.tasks.results.core import InMemoryResultStore, ResultStore
from lexigram.tasks.scheduling.scheduler import TaskScheduler

if TYPE_CHECKING:
    from collections.abc import Callable

    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )
    from lexigram.tasks.models.job import JobProtocol
    from lexigram.tasks.scheduling.templates import JobTemplateProtocol

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Module-level helpers (no self; keep them small and testable)
# ---------------------------------------------------------------------------


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


class TaskProvider(Provider):
    """Task processing provider for Lexigram Framework

    TaskProvider integrates task processing with the Lexigram Framework,
    providing dependency injection, lifecycle management, and health monitoring.

    Example:
        ```python
        from lexigram.app import Application
        from lexigram.tasks import TaskProvider, MemoryTaskQueue

        app = Application()
        queue = MemoryTaskQueue()
        provider = TaskProvider(queue, worker_count=4)
        app.use(provider)

        await app.start()
        ```
    """

    name = "tasks"
    priority = ProviderPriority.INFRASTRUCTURE
    config_key: str | None = "tasks"
    config_model: type | None = TaskConfig

    def __init__(
        self,
        queue: TaskQueueProtocol,
        worker_count: int = 1,
        enable_scheduler: bool = True,
        middleware_pipeline: TaskMiddlewarePipeline | None = None,
    ):
        """Initialize task provider

        Args:
            queue: TaskQueueProtocol implementation to use
            worker_count: Number of workers to create
            enable_scheduler: Whether to enable job scheduling
            middleware_pipeline: Optional middleware pipeline applied to every
                worker in the pool.
        """
        super().__init__()
        self.queue = queue
        self.worker_count = worker_count
        self.enable_scheduler = enable_scheduler
        self._middleware_pipeline = middleware_pipeline

        self.worker_pool: WorkerPool | None = None
        self.scheduler: TaskScheduler | None = None
        self.scheduler_task: asyncio.Task[Any] | None = None

        # Result store — default in-memory; upgraded to CacheBackendResultStore in boot()
        # if a CacheBackendProtocol is available in the container.
        self._result_store: ResultStore = InMemoryResultStore()

        # Handler registry
        self.registry = HandlerRegistry()

        # Backend registry — manages backend type → factory mapping
        self._backend_registry = TaskBackendRegistry.with_defaults()

        # Persisted TaskConfig; set by from_config() — None when the provider
        # was constructed directly via __init__.
        self._config: TaskConfig | None = None

        # Multi-backend: list of (name, queue) 2-tuples accumulated during
        # _register_multi_backend().  Empty in single-backend mode.
        self._queue_services: list[tuple[str, Any]] = []

        # Track background tasks for lifecycle management
        self._background_tasks: set[asyncio.Task[Any]] = set()

    @classmethod
    def from_config(cls, config: TaskConfig, **context: Any) -> TaskProvider:
        """Create a TaskProvider from a TaskConfig.

        Context kwargs may include a pre-built 'queue'. If not provided,
        a MemoryTaskQueue is created as default.
        """
        from lexigram.tasks.backends.memory import MemoryTaskQueue

        queue = context.get("queue") or MemoryTaskQueue()  # type: ignore[abstract]
        provider = cls(
            queue=queue,
            worker_count=(getattr(config.worker, "worker_count", None) or 1),
            enable_scheduler=getattr(
                getattr(config, "scheduler", None), "enabled", True
            ),
        )
        # Store the config so register() can inspect config.backends for
        # multi-backend mode.
        provider._config = config
        return provider

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register task services with the DI container.

        Args:
            container: DI registrar to bind task services into.
        """
        from lexigram.contracts.infra.tasks import TaskProviderProtocol

        self._container = container
        container.singleton(TaskProvider, lambda: self)
        container.singleton(TaskProviderProtocol, lambda: self)
        container.singleton(TaskScheduler, lambda: self.scheduler)
        container.singleton(WorkerPool, lambda: self.worker_pool)
        container.singleton(HandlerRegistry, lambda: self.registry)
        container.singleton(cast("type", TaskExecutorProtocol), lambda: self.registry)
        container.singleton(TaskBackendRegistry, lambda: self._backend_registry)
        container.singleton(TaskMetricsCollector, TaskMetricsCollector())
        # ResultStore: lambda reads self._result_store so it returns the upgraded
        # CacheBackendResultStore if one was injected during boot().
        container.singleton(cast("type", ResultStore), lambda: self._result_store)

        # Branch: multi-backend when config declares named backends; otherwise
        # fall back to the original single-backend behaviour.
        if self._config is not None and self._config.backends:
            await self._register_multi_backend(container)
        else:
            await self._register_single_backend(container)

        await self._discover_backends(container)
        await self._register_admin_widgets(container)

    async def _register_single_backend(
        self, container: ContainerRegistrarProtocol
    ) -> None:
        """Register the single primary queue (existing behaviour, preserved exactly)."""
        container.singleton(cast("type", TaskQueueProtocol), lambda: self.queue)

    async def _register_multi_backend(
        self, container: ContainerRegistrarProtocol
    ) -> None:
        """Register multiple named task queue backends.

        Each entry in ``self._config.backends`` is instantiated via the backend
        registry and registered as a named ``TaskQueueProtocol`` singleton.
        The primary backend (``primary=True`` or the first entry by identity)
        also receives the unnamed ``TaskQueueProtocol`` binding for backward
        compatibility.

        Args:
            container: DI registrar to bind task services into.
        """
        assert self._config is not None  # guarded by caller  # noqa: S101

        for entry in self._config.backends:
            backend_cfg = TaskConfig.from_named(entry)
            queue = self._backend_registry.create_backend(backend_cfg)
            self._queue_services.append((entry.name, queue))

            # Named binding — resolvable via Annotated[TaskQueueProtocol, Named(entry.name)]
            container.singleton(
                cast("type", TaskQueueProtocol),
                factory=lambda q=queue: q,  # default-arg capture avoids late-binding
                name=entry.name,
            )

            # Primary backend also gets the unnamed binding for backward compat.
            # Use identity check (is), NOT equality (==).
            if entry.primary or self._config.backends[0] is entry:
                container.singleton(
                    cast("type", TaskQueueProtocol),
                    factory=lambda q=queue: q,
                )

        logger.info(
            "tasks_multi_backend_registered",
            count=len(self._config.backends),
            names=[e.name for e in self._config.backends],
        )

    async def _discover_backends(self, container: ContainerRegistrarProtocol) -> None:
        """Scan the ``lexigram.tasks.backends`` entry-point group.

        Any entry point that resolves to a
        :class:`~lexigram.di.provider.Provider` subclass is instantiated
        and its :meth:`~lexigram.di.provider.Provider.register` method is
        called, allowing third-party backend packages to self-register.

        Args:
            container: The DI container registrar.
        """
        import importlib.metadata as _meta

        from lexigram.di.provider import Provider as _Provider

        eps = _meta.entry_points(group="lexigram.tasks.backends")
        for ep in eps:
            try:
                candidate = ep.load()
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "tasks_ep_load_failed",
                    entry_point=ep.name,
                    error=str(exc),
                )
                continue
            if not (isinstance(candidate, type) and issubclass(candidate, _Provider)):
                logger.debug(
                    "tasks_ep_skipped",
                    entry_point=ep.name,
                    reason="not a Provider subclass",
                )
                continue
            logger.debug(
                "tasks_ep_found",
                entry_point=ep.name,
                provider=candidate.__name__,
            )
            try:
                await candidate().register(container)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "tasks_ep_register_failed",
                    entry_point=ep.name,
                    provider=candidate.__name__,
                    error=str(exc),
                )

    async def _register_admin_widgets(
        self, container: ContainerRegistrarProtocol
    ) -> None:
        """Register admin widget handlers and contributor.

        Args:
            container: The DI container registrar.
        """
        # Register handlers as transient
        container.transient(
            TasksSummaryWidgetHandler,
            factory=lambda: TasksSummaryWidgetHandler(
                queue_provider=self.queue, pool_provider=self.worker_pool
            ),
        )
        container.transient(
            AvgDurationWidgetHandler,
            factory=lambda: AvgDurationWidgetHandler(pool_provider=self.worker_pool),
        )

        # Register the contributor as singleton
        container.singleton(TasksAdminContributor, TasksAdminContributor)

        # Register contributor in admin registry
        container.singleton(
            AdminContributorProtocol,
            lambda: container.resolve(TasksAdminContributor),  # type: ignore[attr-defined]
            name="tasks",
        )

        logger.debug("tasks_admin_widgets_registered")

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

    def register_handler(self, task_name: str, handler: Callable[..., Any]) -> None:
        """Register a task handler

        Args:
            task_name: Name of the task type
            handler: Async handler function
        """
        self.registry.register(task_name, handler)
        logger.info("Registered handler for task: %s", task_name)

    def build_idempotency_manager(
        self,
        storage: IdempotencyStoreProtocol,
    ) -> IdempotencyManagerProtocol:
        """Build an idempotency manager over *storage* (see contract)."""
        return IdempotencyManager(storage=storage)

    def build_idempotent_task_manager(
        self,
        queue_client: TaskQueueProtocol,
        idempotency_manager: IdempotencyManagerProtocol,
    ) -> IdempotentTaskManagerProtocol:
        """Build an idempotent task manager (see contract)."""
        return IdempotentTaskManager(
            queue_client=queue_client,
            idempotency_manager=idempotency_manager,
        )

    def register_scheduled_task(self, task_func: Any) -> None:
        """Register a decorated task function for scheduling.

        Validates that the task has required metadata (_task_name and _cron).
        Registration is atomic: if scheduling fails, the handler is rolled back.

        Args:
            task_func: Task function decorated with @scheduled

        Raises:
            TaskRegistrationError: If _task_name or _cron is missing
        """
        task_name = getattr(task_func, "_task_name", None)
        if task_name is None:
            raise TaskRegistrationError(
                f"register_scheduled_task: object {task_func!r} lacks _task_name "
                "(was @scheduled decorator applied correctly?)"
            )

        cron = getattr(task_func, "_cron", None)
        if cron is None:
            raise TaskRegistrationError(
                f"register_scheduled_task: task {task_name!r} lacks _cron — "
                "use @task() for non-scheduled handlers"
            )

        self.register_handler(task_name, task_func)
        try:
            if self.enable_scheduler:
                self.schedule_job_sync(
                    job_template=task_func.signature(), cron_expression=cron
                )
        except Exception:
            self.registry.unregister(task_name)
            raise

    async def enqueue_job(self, job: JobProtocol) -> str:
        """Enqueue a job for processing"""
        await self.queue.enqueue(job)
        return job.id

    async def _enqueue_job(self, job: JobProtocol) -> None:
        """Internal method to enqueue jobs (used by scheduler)"""
        await self.enqueue_job(job)

    def schedule_job_sync(
        self,
        job_template: JobProtocol | JobTemplateProtocol,
        cron_expression: str,
        job_id: str | None = None,
    ) -> str | None:
        """Schedule a job with cron expression"""
        if self.scheduler:
            return self.scheduler.schedule_job_sync(
                job_template, cron_expression, job_id
            )
        logger.warning("Scheduler not enabled")
        return None

    def unschedule_job_sync(self, job_id: str) -> bool:
        """Remove a scheduled job"""
        if self.scheduler:
            return self.scheduler.unschedule_job_sync(job_id)
        return False

    def get_worker_stats(self) -> dict[str, Any] | None:
        """Get worker pool statistics"""
        if self.worker_pool:
            return self.worker_pool.get_pool_stats()
        return None

    def get_scheduled_jobs(self) -> dict[str, Any] | None:
        """Get scheduled jobs information"""
        if self.scheduler:
            return {
                "scheduled_jobs": [
                    {
                        "job_id": job_id,
                        "name": scheduled.job_template.name,
                        "cron": scheduled.cron_expression,
                        "next_run": scheduled.next_run,
                        "enabled": scheduled.enabled,
                    }
                    for job_id, scheduled in self.scheduler.scheduled_jobs.items()
                ],
            }
        return None

    def refresh_worker_handlers(self) -> None:
        """Refresh handler mappings in all workers.

        Call this after registering new handlers to ensure workers
        can execute jobs registered after pool creation.
        """
        if self.worker_pool:
            self.worker_pool.refresh_handlers()


__all__ = ["TaskProvider"]
