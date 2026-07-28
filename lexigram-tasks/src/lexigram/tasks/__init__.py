"""Lexigram Tasks - Background Processing and Task Scheduling.

A comprehensive background task processing system for the Lexigram Framework,
providing task scheduling, job queues, worker management, and monitoring capabilities.

This package follows the Root File Pattern for consistent structure:
- protocols.py: TaskQueueProtocol protocol and abstractions
- types.py: Shared type definitions (Priority)
- config.py: Task configuration settings
- exceptions.py: Task-specific exceptions
- provider.py: Framework integration via provider pattern

Subpackages:
- models/: JobProtocol and Task data models
- backends/: Task queue implementations (memory, Redis, RabbitMQ)
- execution/: Worker pool management, task execution, and health monitoring
- scheduling/: Cron-based job scheduling and templates
- concurrency/: Rate limiting and distributed locking
- workflows/: Task chaining, groups, chords, and conditionals
- middleware/: Pre/post execution hooks and middleware
- progress/: Real-time task progress tracking
- dlq/: Dead letter queue management
- results/: Task result store with async wait
- observability/: Dashboard metrics and execution history
"""

from __future__ import annotations

import importlib.metadata
from typing import TYPE_CHECKING, Any

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from lexigram.tasks.constants import __version__ as __version__

if TYPE_CHECKING:
    from lexigram.contracts.infra.tasks import TaskExecutorProtocol, TaskQueueProtocol
    from lexigram.tasks.backends import (
        MemoryTaskQueue,
        RabbitMQTaskQueue,
        RedisTaskQueue,
    )
    from lexigram.tasks.background_task_manager import BackgroundTaskManager
    from lexigram.tasks.concurrency import (
        DistributedLockProtocol,
        GlobalRateLimiter,
        QueueRateLimiter,
        UniqueTask,
        distributed_lock,
    )
    from lexigram.tasks.config import (
        NamedTaskConfig,
        TaskBackendConfig,
        TaskConfig,
        TaskRateLimitConfig,
        TaskSchedulerConfig,
        TaskTimeoutConfig,
        TaskWorkerConfig,
    )
    from lexigram.tasks.decorators import scheduled, task
    from lexigram.tasks.di.factories import (
        create_memory_task_provider,
        create_provider_from_config,
        create_rabbitmq_task_provider,
        create_redis_task_provider,
    )
    from lexigram.tasks.di.provider import TaskProvider
    from lexigram.tasks.dispatch import delay
    from lexigram.tasks.dlq import DeadLetterQueue, FailureRecord
    from lexigram.tasks.exceptions import (
        TaskCancelledError,
        TaskError,
        TaskExecutionError,
        TaskNotFoundError,
        TaskTimeoutError,
        TaskValidationError,
    )
    from lexigram.tasks.execution import (
        HandlerRegistry,
        TaskHealth,
        TaskWorker,
        TaskWorkerServices,
        WorkerJobStats,
        WorkerPool,
    )
    from lexigram.tasks.middleware import (
        LoggingMiddleware,
        MetricsMiddleware,
        TaskExecutionContext,
        TaskMiddleware,
        TaskMiddlewarePipeline,
        TimeoutMiddleware,
    )
    from lexigram.tasks.models import JobProtocol, JobResult, JobStatus
    from lexigram.tasks.observability import ExecutionRecord, TaskDashboard
    from lexigram.tasks.progress import (
        CacheBackendProgressStore,
        InMemoryProgressStore,
        InMemoryProgressTracker,
        ProgressInfo,
        ProgressSnapshot,
        ProgressStatus,
        ProgressStore,
        ProgressTracker,
        ProgressTrackerProtocol,
    )
    from lexigram.tasks.results import (
        CacheBackendResultStore,
        InMemoryResultStore,
        ResultStore,
    )
    from lexigram.tasks.scheduled_worker import OnErrorPolicy, ScheduledWorker
    from lexigram.tasks.scheduling import (
        CronExpression,
        JobTemplateProtocol,
        ScheduledJob,
        TaskScheduler,
    )
    from lexigram.tasks.types import Priority
    from lexigram.tasks.workflows import (
        BranchStep,
        StepResult,
        TaskChain,
        TaskChord,
        TaskGroup,
        TaskStep,
        WorkflowResult,
        WorkflowStatus,
        chain,
    )

_LAZY_SUBMODULES = {
    "concurrency": "lexigram.tasks.concurrency",
    "execution": "lexigram.tasks.execution",
    "scheduling": "lexigram.tasks.scheduling",
    "models": "lexigram.tasks.models",
    "backends": "lexigram.tasks.backends",
    "workflows": "lexigram.tasks.workflows",
    "middleware": "lexigram.tasks.middleware",
    "progress": "lexigram.tasks.progress",
    "dlq": "lexigram.tasks.dlq",
    "results": "lexigram.tasks.results",
    "observability": "lexigram.tasks.observability",
}

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # BackgroundTaskManager + ScheduledWorker (LEX-006 / LEX-005)
    "BackgroundTaskManager": (
        "lexigram.tasks.background_task_manager",
        "BackgroundTaskManager",
    ),
    "ScheduledWorker": ("lexigram.tasks.scheduled_worker", "ScheduledWorker"),
    "OnErrorPolicy": ("lexigram.tasks.scheduled_worker", "OnErrorPolicy"),
    # Module
    "TasksModule": ("lexigram.tasks.module", "TasksModule"),
    "JobProtocol": ("lexigram.tasks.models", "JobProtocol"),
    "JobStatus": ("lexigram.tasks.models", "JobStatus"),
    "JobResult": ("lexigram.tasks.models", "JobResult"),
    "Priority": ("lexigram.tasks.types", "Priority"),
    "TaskError": ("lexigram.tasks.exceptions", "TaskError"),
    "QueueFullError": ("lexigram.tasks.exceptions", "QueueFullError"),
    "TaskNotFoundError": ("lexigram.tasks.exceptions", "TaskNotFoundError"),
    "TaskTimeoutError": ("lexigram.tasks.exceptions", "TaskTimeoutError"),
    "TaskCancelledError": ("lexigram.tasks.exceptions", "TaskCancelledError"),
    "TaskExecutionError": ("lexigram.tasks.exceptions", "TaskExecutionError"),
    "TaskValidationError": ("lexigram.tasks.exceptions", "TaskValidationError"),
    "TaskConfig": ("lexigram.tasks.config", "TaskConfig"),
    "NamedTaskConfig": ("lexigram.tasks.config", "NamedTaskConfig"),
    "TaskBackendConfig": ("lexigram.tasks.config", "TaskBackendConfig"),
    "TaskWorkerConfig": ("lexigram.tasks.config", "TaskWorkerConfig"),
    "TaskSchedulerConfig": ("lexigram.tasks.config", "TaskSchedulerConfig"),
    "TaskRateLimitConfig": ("lexigram.tasks.config", "TaskRateLimitConfig"),
    "TaskTimeoutConfig": ("lexigram.tasks.config", "TaskTimeoutConfig"),
    "TaskQueueProtocol": ("lexigram.contracts.infra.tasks", "TaskQueueProtocol"),
    "TaskExecutorProtocol": ("lexigram.contracts.infra.tasks", "TaskExecutorProtocol"),
    "MemoryTaskQueue": ("lexigram.tasks.backends", "MemoryTaskQueue"),
    "RedisTaskQueue": ("lexigram.tasks.backends", "RedisTaskQueue"),
    "RabbitMQTaskQueue": ("lexigram.tasks.backends", "RabbitMQTaskQueue"),
    "TaskWorker": ("lexigram.tasks.execution", "TaskWorker"),
    "TaskWorkerServices": ("lexigram.tasks.execution", "TaskWorkerServices"),
    "WorkerJobStats": ("lexigram.tasks.execution", "WorkerJobStats"),
    "WorkerPool": ("lexigram.tasks.execution", "WorkerPool"),
    "HandlerRegistry": ("lexigram.tasks.execution", "HandlerRegistry"),
    "TaskHealth": ("lexigram.tasks.execution", "TaskHealth"),
    "TaskScheduler": ("lexigram.tasks.scheduling", "TaskScheduler"),
    "ScheduledJob": ("lexigram.tasks.scheduling", "ScheduledJob"),
    "CronExpression": ("lexigram.tasks.scheduling", "CronExpression"),
    "JobTemplateProtocol": ("lexigram.tasks.scheduling", "JobTemplateProtocol"),
    "TaskProvider": ("lexigram.tasks.di.provider", "TaskProvider"),
    "create_provider_from_config": (
        "lexigram.tasks.di.provider",
        "create_provider_from_config",
    ),
    "create_memory_task_provider": (
        "lexigram.tasks.di.provider",
        "create_memory_task_provider",
    ),
    "create_redis_task_provider": (
        "lexigram.tasks.di.provider",
        "create_redis_task_provider",
    ),
    "create_rabbitmq_task_provider": (
        "lexigram.tasks.di.provider",
        "create_rabbitmq_task_provider",
    ),
    "QueueRateLimiter": ("lexigram.tasks.concurrency", "QueueRateLimiter"),
    "GlobalRateLimiter": ("lexigram.tasks.concurrency", "GlobalRateLimiter"),
    "DistributedLockProtocol": (
        "lexigram.tasks.concurrency",
        "DistributedLockProtocol",
    ),
    "UniqueTask": ("lexigram.tasks.concurrency", "UniqueTask"),
    "distributed_lock": ("lexigram.tasks.concurrency", "distributed_lock"),
    "task": ("lexigram.tasks.decorators", "task"),
    "scheduled": ("lexigram.tasks.decorators", "scheduled"),
    # Dispatch
    "delay": ("lexigram.tasks.dispatch", "delay"),
    # Workflows
    "TaskChain": ("lexigram.tasks.workflows", "TaskChain"),
    "TaskGroup": ("lexigram.tasks.workflows", "TaskGroup"),
    "TaskChord": ("lexigram.tasks.workflows", "TaskChord"),
    "TaskStep": ("lexigram.tasks.workflows", "TaskStep"),
    "BranchStep": ("lexigram.tasks.workflows", "BranchStep"),
    "WorkflowResult": ("lexigram.tasks.workflows", "WorkflowResult"),
    "WorkflowStatus": ("lexigram.tasks.workflows", "WorkflowStatus"),
    "StepResult": ("lexigram.tasks.workflows", "StepResult"),
    "chain": ("lexigram.tasks.workflows", "chain"),
    # Middleware
    "TaskMiddlewarePipeline": (
        "lexigram.tasks.middleware",
        "TaskMiddlewarePipeline",
    ),
    "TaskMiddleware": ("lexigram.tasks.middleware", "TaskMiddleware"),
    "TaskExecutionContext": (
        "lexigram.tasks.middleware",
        "TaskExecutionContext",
    ),
    "LoggingMiddleware": ("lexigram.tasks.middleware", "LoggingMiddleware"),
    "MetricsMiddleware": ("lexigram.tasks.middleware", "MetricsMiddleware"),
    "TimeoutMiddleware": ("lexigram.tasks.middleware", "TimeoutMiddleware"),
    # Progress
    "ProgressTracker": ("lexigram.tasks.progress", "ProgressTracker"),
    "ProgressStore": ("lexigram.tasks.progress", "ProgressStore"),
    "InMemoryProgressStore": ("lexigram.tasks.progress", "InMemoryProgressStore"),
    "InMemoryProgressTracker": ("lexigram.tasks.progress", "InMemoryProgressTracker"),
    "ProgressInfo": ("lexigram.tasks.progress", "ProgressInfo"),
    "ProgressSnapshot": ("lexigram.tasks.progress", "ProgressSnapshot"),
    "ProgressStatus": ("lexigram.tasks.progress", "ProgressStatus"),
    "ProgressTrackerProtocol": ("lexigram.tasks.progress", "ProgressTrackerProtocol"),
    "CacheBackendProgressStore": (
        "lexigram.tasks.progress",
        "CacheBackendProgressStore",
    ),
    # DLQ
    "DeadLetterQueue": ("lexigram.tasks.dlq", "DeadLetterQueue"),
    "FailureRecord": ("lexigram.tasks.dlq", "FailureRecord"),
    # Results
    "ResultStore": ("lexigram.tasks.results", "ResultStore"),
    "InMemoryResultStore": ("lexigram.tasks.results", "InMemoryResultStore"),
    "CacheBackendResultStore": ("lexigram.tasks.results", "CacheBackendResultStore"),
    # Observability
    "TaskDashboard": ("lexigram.tasks.observability", "TaskDashboard"),
    "ExecutionRecord": ("lexigram.tasks.observability", "ExecutionRecord"),
    # Events
    "TaskQueuedEvent": ("lexigram.tasks.events", "TaskQueuedEvent"),
    "TaskCompletedEvent": ("lexigram.tasks.events", "TaskCompletedEvent"),
    "TaskFailedEvent": ("lexigram.tasks.events", "TaskFailedEvent"),
    # Hooks
    "TaskCompletedHook": ("lexigram.tasks.hooks", "TaskCompletedHook"),
    "TaskEnqueuedHook": ("lexigram.tasks.hooks", "TaskEnqueuedHook"),
    "TaskFailedHook": ("lexigram.tasks.hooks", "TaskFailedHook"),
    "TaskStartedHook": ("lexigram.tasks.hooks", "TaskStartedHook"),
}


def __getattr__(name: str) -> Any:
    """Lazy load attributes to avoid circular imports."""
    import importlib

    # Check if it's a lazy class first
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value

    # Check if it's a submodule request
    if name in _LAZY_SUBMODULES:
        return importlib.import_module(_LAZY_SUBMODULES[name])

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """List available attributes for IDE support."""
    return sorted(
        set(__all__) | set(_LAZY_SUBMODULES.keys()) | set(_LAZY_IMPORTS.keys())
    )


__all__ = list(_LAZY_SUBMODULES.keys()) + list(_LAZY_IMPORTS.keys())
