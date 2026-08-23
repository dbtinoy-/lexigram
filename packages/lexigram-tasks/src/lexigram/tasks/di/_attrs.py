"""Shared attribute surface for TaskProvider mixins."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from lexigram.contracts.core.di import ContainerRegistrarProtocol
from lexigram.contracts.core.logging import LoggerProtocol
from lexigram.contracts.infra.tasks.protocols import TaskQueueProtocol
from lexigram.tasks.backends.registry import TaskBackendRegistry
from lexigram.tasks.config import TaskConfig
from lexigram.tasks.execution.pool import WorkerPool
from lexigram.tasks.execution.registry import HandlerRegistry
from lexigram.tasks.middleware.core import TaskMiddlewarePipeline
from lexigram.tasks.results.core import ResultStore
from lexigram.tasks.scheduling.scheduler import TaskScheduler

if TYPE_CHECKING:
    from lexigram.contracts.core.identity import IdGeneratorProtocol
    from lexigram.tasks.models.job import JobProtocol


class _TaskAttrsMixin:
    """Attribute contract shared by all TaskProvider mixins."""

    _backend_registry: TaskBackendRegistry
    _background_tasks: set[asyncio.Task[Any]]
    _config: TaskConfig | None
    _container: ContainerRegistrarProtocol
    _id_generator: IdGeneratorProtocol | None
    _middleware_pipeline: TaskMiddlewarePipeline | None
    _queue_services: list[tuple[str, Any]]
    _result_store: ResultStore
    enable_scheduler: bool
    logger: LoggerProtocol
    name: str
    queue: TaskQueueProtocol
    registry: HandlerRegistry
    scheduler: TaskScheduler | None
    scheduler_task: asyncio.Task[Any] | None
    worker_count: int
    worker_pool: WorkerPool | None

    if TYPE_CHECKING:

        async def _enqueue_job(self, job: JobProtocol) -> None: ...
