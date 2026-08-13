"""Task and job queue protocol class definitions."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, runtime_checkable

if TYPE_CHECKING:
    from lexigram.contracts.core import HealthCheckResult
    from lexigram.contracts.core.idempotency import IdempotencyStoreProtocol
    from lexigram.contracts.core.result import Result
    from lexigram.contracts.infra.tasks.enums import JobStatus
    from lexigram.contracts.infra.tasks.exceptions import TaskQueueError
    from lexigram.contracts.infra.tasks.idempotency import IdempotencyResult

T = TypeVar("T")


@runtime_checkable
class TaskManagerProtocol(Protocol):
    """Shared background-task management service.

    Implemented by ``lexigram.tasks.background_task_manager.BackgroundTaskManager``
    (LEX-006).  Consumers resolve this protocol from the container instead of
    importing the implementation package (e.g. ``lexigram.monitor``).
    """

    def track(self, coro: Awaitable[T]) -> asyncio.Task[T]:
        """Track a coroutine as a background task."""

    def track_named(self, name: str, coro: Awaitable[T]) -> asyncio.Task[T]:
        """Track a coroutine as a named background task."""

    @property
    def pending_count(self) -> int:
        """Return the number of tracked, unfinished tasks."""

    async def shutdown(self, timeout: float = 30.0) -> None:
        """Cancel all tracked tasks and wait for completion within *timeout*."""


@runtime_checkable
class JobProtocol(Protocol):
    """Protocol for JobProtocol objects."""

    id: str
    name: str
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    priority: int
    status: JobStatus
    max_retries: int
    timeout: float | None
    correlation_id: str | None
    causation_id: str | None


@runtime_checkable
class TaskQueueProtocol(Protocol):
    """Protocol for task queue implementations.

    This defines the contract for background task queues
    (Redis-based, PostgreSQL-based, in-memory, etc.).

    Example:
        ```python
        class RedisTaskQueue:
            async def enqueue(self, task: Task) -> str:
                task_id = str(uuid4())
                await self._redis.rpush("tasks", task.to_json())
                return task_id

            async def dequeue(self) -> Task | None:
                data = await self._redis.lpop("tasks")
                return Task.from_json(data) if data else None
        ```
    """

    async def enqueue(self, task: Any) -> Result[str, TaskQueueError]:
        """Add a task to the queue.

        Args:
            task: Task instance to enqueue.

        Returns:
            Ok(task_id) on success; Err(TaskQueueError) if the queue reports
            a recoverable failure (e.g. full queue, invalid payload).  Only
            infrastructure failures (lost connection) are raised as exceptions.
        """
        ...

    async def dequeue(self) -> Any | None:
        """Remove and return the next task.

        Returns:
            Next Task or None if queue is empty.
        """
        ...

    async def get_task_count(self) -> int:
        """Get the number of tasks in the queue.

        Returns:
            Number of pending tasks.
        """
        ...

    async def clear(self) -> None:
        """Clear all tasks from the queue."""
        ...

    async def get_job(self, job_id: str) -> Any | None:
        """Get a job by ID.

        Args:
            job_id: Unique job identifier.

        Returns:
            Job data or None if not found.
        """
        ...

    async def delete_job(self, job_id: str) -> bool:
        """Delete a job from the queue.

        Args:
            job_id: Unique job identifier.

        Returns:
            True if the job was deleted.
        """
        ...

    async def count(self, queue_name: str, status: Any | None = None) -> int:
        """Count queued jobs.

        Args:
            queue_name: Queue to inspect.
            status: Optional status filter.

        Returns:
            Number of matching jobs.
        """
        ...

    async def ack(self, task_id: str) -> None:
        """Acknowledge successful processing of a dequeued task.

        Signals that the task has been processed successfully and can
        be permanently discarded from any in-flight tracking.

        Args:
            task_id: ID of the task to acknowledge.
        """
        ...

    async def nack(self, task_id: str, requeue: bool = True) -> None:
        """Negative-acknowledge a dequeued task.

        Signals that the task could not be processed. The task is
        optionally requeued for another processing attempt.

        Args:
            task_id: ID of the task to negative-acknowledge.
            requeue: If True, return the task to the queue for retry.
                If False, discard the task permanently.
        """
        ...

    async def close(self) -> None:
        """Close the queue connection and cleanup resources."""
        ...


@runtime_checkable
class TaskExecutorProtocol(Protocol):
    """Protocol for task executor implementations.

    Executors process tasks from a queue by dispatching
    them to registered handlers.

    Example:
        ```python
        class TaskExecutorProtocol:
            async def execute(self, task: Task) -> Any:
                handler = self._handlers.get(task.name)
                if handler:
                    return await handler(task.payload)
                raise UnknownTaskError(task.name)
        ```
    """

    async def execute(self, task: Any) -> Any:
        """Execute a task using the registered handler.

        Args:
            task: Task to execute.

        Returns:
            Task execution result.

        Raises:
            UnknownTaskError: If no handler registered for task.
        """
        ...

    def register_handler(self, task_name: str, handler: Any) -> None:
        """Register a handler for a task type.

        Args:
            task_name: Name of the task type.
            handler: Async callable to handle the task.
        """
        ...

    def get_handler(self, task_name: str) -> Any | None:
        """Get the handler for a task type.

        Args:
            task_name: Name of the task type.

        Returns:
            Handler if registered, None otherwise.
        """
        ...


@runtime_checkable
class TaskProviderProtocol(Protocol):
    """Protocol for task provider implementations.

    Task providers integrate task processing with the framework,
    providing dependency injection, lifecycle management, and health monitoring.
    """

    async def register(self, container: Any) -> None:
        """Register task services with the DI container.

        Args:
            container: DI container to register services in.
        """
        ...

    async def boot(self, container: Any | None = None) -> None:
        """Start the task provider.

        Called by the framework on application startup.

        Args:
            container: Optional DI container.
        """
        ...

    async def shutdown(self, app: Any) -> None:
        """Shutdown the task provider gracefully.

        Called by the framework on application shutdown.

        Args:
            app: Application instance.
        """
        ...

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check task provider health.

        Returns:
            HealthCheckResult with current status and metrics.
        """
        ...

    def register_handler(self, task_name: str, handler: Any) -> None:
        """Register a task handler.

        Args:
            task_name: Name of the task type.
            handler: Async handler function.
        """
        ...

    def register_scheduled_task(self, task_func: Any) -> None:
        """Register a decorated task function for scheduling.

        Args:
            task_func: Task function decorated with @scheduled.
        """
        ...

    async def enqueue_job(self, job: Any) -> str:
        """Enqueue a job for processing.

        Args:
            job: JobProtocol instance to enqueue.

        Returns:
            JobProtocol ID.
        """
        ...

    def build_idempotency_manager(
        self,
        storage: IdempotencyStoreProtocol,
    ) -> IdempotencyManagerProtocol:
        """Build an idempotency manager over *storage*.

        Cross-package consumers (e.g. ``lexigram-multimedia``) build the
        idempotency machinery through this factory instead of importing
        ``lexigram-tasks`` internals directly.

        Args:
            storage: Storage backend for idempotency keys.

        Returns:
            An :class:`IdempotencyManagerProtocol` implementation bound to
            *storage*.
        """
        ...

    def build_idempotent_task_manager(
        self,
        queue_client: Any,
        idempotency_manager: IdempotencyManagerProtocol,
    ) -> IdempotentTaskManagerProtocol:
        """Build an idempotent task manager over *queue_client*.

        Cross-package consumers (e.g. ``lexigram-multimedia``) obtain their
        duplicate-protected task submitter through this factory instead of
        importing ``lexigram-tasks`` internals directly.

        Args:
            queue_client: Task queue client (``TaskQueueProtocol``) to
                submit jobs through.
            idempotency_manager: Idempotency manager detecting duplicates.

        Returns:
            An :class:`IdempotentTaskManagerProtocol` implementation.
        """
        ...

    def schedule_job(
        self,
        job_template: Any,
        cron_expression: str,
        job_id: str | None = None,
    ) -> str | None:
        """Schedule a job with cron expression.

        Args:
            job_template: JobProtocol or JobTemplateProtocol instance.
            cron_expression: Cron expression for scheduling.
            job_id: Optional job ID.

        Returns:
            Scheduled job ID if successful, None otherwise.
        """
        ...

    def unschedule_job(self, job_id: str) -> bool:
        """Remove a scheduled job.

        Args:
            job_id: JobProtocol ID to unschedule.

        Returns:
            True if job was unscheduled, False otherwise.
        """
        ...

    def get_worker_stats(self) -> dict[str, Any] | None:
        """Get worker pool statistics.

        Returns:
            Dictionary with worker statistics or None.
        """
        ...

    def get_scheduled_jobs(self) -> dict[str, Any] | None:
        """Get scheduled jobs information.

        Returns:
            Dictionary with scheduled jobs info or None.
        """
        ...


@runtime_checkable
class JobTemplateProtocol(Protocol):
    """Protocol for JobTemplateProtocol objects."""

    name: str
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    priority: int
    max_retries: int
    timeout: float | None
    depends_on: list[str]


@runtime_checkable
class TaskWorkerProtocol(Protocol):
    """Protocol for task worker implementations.

    Workers consume tasks from a queue and execute them.
    """

    def __init__(
        self,
        worker_id: str,
        queue: Any,
        handler_registry: dict[str, Any],
    ) -> None:
        """Initialize worker."""
        ...

    async def start(self) -> None:
        """Start the worker."""
        ...

    async def stop(self) -> None:
        """Stop the worker."""
        ...


@runtime_checkable
class DLQProtocol(Protocol):
    """Protocol for Dead Letter Queue implementations."""

    async def add(
        self,
        message_id: str,
        payload: Any,
        reason: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a failed message to the DLQ."""
        ...

    async def get(self, message_id: str) -> dict[str, Any] | None:
        """Retrieve a failed message by ID."""
        ...

    async def retry(self, message_id: str) -> bool:
        """Move a failed message back to the main queue for reprocessing."""
        ...

    async def purge(self, message_id: str) -> bool:
        """Permanently delete a failed message from the DLQ."""
        ...

    async def clear(self) -> int:
        """Remove all failed messages and return the count removed."""
        ...

    async def size(self) -> int:
        """Return the number of messages currently in the DLQ."""
        ...

    async def list_failed(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List failed messages with pagination."""
        ...


@runtime_checkable
class IdempotencyManagerProtocol(Protocol):
    """Manages idempotency keys for task submissions.

    Implementations (e.g. ``lexigram-tasks``
    :class:`~lexigram.tasks.execution.manager.IdempotencyManager`) generate
    deterministic keys from task parameters and detect duplicate
    submissions against an :class:`IdempotencyStoreProtocol` backend.
    """

    def generate_key(
        self,
        task_name: str,
        params: dict[str, Any],
        client_key: str | None = None,
    ) -> str:
        """Generate an idempotency key from task name and parameters.

        Args:
            task_name: Name of the task.
            params: Task parameters.
            client_key: Optional client-provided key; returned verbatim.

        Returns:
            A deterministic idempotency key.
        """
        ...

    async def check_duplicate(
        self,
        idempotency_key: str,
    ) -> IdempotencyResult | None:
        """Check whether a key was already submitted.

        Args:
            idempotency_key: The idempotency key to look up.

        Returns:
            The previous :class:`IdempotencyResult` when a duplicate exists,
            ``None`` otherwise.
        """
        ...

    async def record_submission(
        self,
        idempotency_key: str,
        task_id: str,
        task_name: str,
        params: dict[str, Any],
    ) -> None:
        """Record a task submission under *idempotency_key*."""
        ...

    async def record_completion(
        self,
        idempotency_key: str,
        result: Any,
    ) -> None:
        """Record the completion result for *idempotency_key*."""
        ...


@runtime_checkable
class IdempotentTaskManagerProtocol(Protocol):
    """Task manager with idempotency protection.

    Implementations (e.g. ``lexigram-tasks``
    :class:`~lexigram.tasks.execution.manager.IdempotentTaskManager`)
    enqueue tasks while preventing duplicate submissions under the same
    idempotency key.
    """

    async def submit_task(
        self,
        task_name: str,
        params: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> IdempotencyResult:
        """Submit a task with idempotency protection.

        Args:
            task_name: Name of the task to submit.
            params: Task parameters.
            idempotency_key: Optional client-provided idempotency key.

        Returns:
            The submission :class:`IdempotencyResult` — a duplicate
            submission returns the previously stored result.

        Example:
            ```python
            result = await manager.submit_task(
                "tts_generation",
                {"text": "hello"},
                idempotency_key="user-42:tts-1",
            )
            if result.status == "duplicate":
                print("already submitted:", result.task_id)
            ```
        """
        ...


__all__ = [
    "DLQProtocol",
    "IdempotencyManagerProtocol",
    "IdempotentTaskManagerProtocol",
    "JobProtocol",
    "JobTemplateProtocol",
    "TaskExecutorProtocol",
    "TaskProviderProtocol",
    "TaskQueueProtocol",
    "TaskWorkerProtocol",
]
