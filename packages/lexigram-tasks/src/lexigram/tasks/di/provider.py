"""Task provider for Lexigram Framework integration

This module provides the TaskProvider for DI container integration.
"""

from __future__ import annotations

import asyncio
from typing import Any

from lexigram.contracts.core import (
    ProviderPriority,
)
from lexigram.contracts.infra.tasks import (
    TaskQueueProtocol,
)
from lexigram.di.provider import Provider
from lexigram.logging import get_logger
from lexigram.tasks.backends.registry import TaskBackendRegistry
from lexigram.tasks.config import TaskConfig
from lexigram.tasks.execution.pool import WorkerPool
from lexigram.tasks.execution.registry import HandlerRegistry
from lexigram.tasks.middleware.core import TaskMiddlewarePipeline
from lexigram.tasks.results.core import InMemoryResultStore, ResultStore
from lexigram.tasks.scheduling.scheduler import TaskScheduler

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Module-level helpers (no self; keep them small and testable)
# ---------------------------------------------------------------------------



from lexigram.tasks.di._lifecycle import (  # noqa: F401 — re-export
    _check_queue_health,  # noqa: F401 — re-export
    _connect_queue,  # noqa: F401 — re-export
    _TaskLifecycleMixin,
    _wire_queue_hooks,  # noqa: F401 — re-export
)
from lexigram.tasks.di._operations import _TaskOperationsMixin
from lexigram.tasks.di._registration import _TaskRegistrationMixin


class TaskProvider(
    _TaskLifecycleMixin,
    _TaskOperationsMixin,
    _TaskRegistrationMixin,
    Provider,
):
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
