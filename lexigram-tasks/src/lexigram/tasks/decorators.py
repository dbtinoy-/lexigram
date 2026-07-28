"""Task decorator for simplified task definition.

Provides a convenient decorator for defining tasks with automatic registration.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol, cast

from lexigram.tasks.models import JobProtocol
from lexigram.tasks.models.job import JobProtocol
from lexigram.tasks.types import Priority

if TYPE_CHECKING:
    from lexigram.contracts.infra.tasks import TaskQueueProtocol

    class TaskFunction(Protocol):
        def __call__(self, *args: Any, **kwargs: Any) -> Any: ...

        @classmethod
        def signature(cls, *args: Any, **kwargs: Any) -> JobProtocol: ...

        @classmethod
        async def apply_async(
            cls,
            queue: TaskQueueProtocol,
            *args: Any,
            **kwargs: Any,
        ) -> Any: ...


def task(
    name: str | None = None,
    priority: Priority | int = Priority.NORMAL,
    max_retries: int = 3,
    timeout: float | None = None,
    queue: str = "default",
    idempotency_key: str | None = None,
) -> Callable[[Callable[..., Any]], Any]:
    """Decorator to define a task.

    Converts a regular function into a task that can be enqueued and executed
    by workers.

    Args:
        name: Task name (defaults to function name)
        priority: Task priority (HIGH, NORMAL, LOW)
        max_retries: Maximum retry attempts on failure
        timeout: Execution timeout in seconds
        queue: Queue name for this task
        idempotency_key: Optional key for idempotent execution

    Returns:
        Decorated function with .delay() and .apply_async() methods
    """

    def decorator(func: Callable[..., Any]) -> TaskFunction:
        task_name = name or func.__name__

        class TaskFunction:
            """Wrapped task function with queue methods."""

            # Store task metadata
            _func = staticmethod(func)
            _task_name = task_name
            # Normalize priority to integer at decoration time to avoid union-attr mypy errors
            _priority = (
                priority
                if isinstance(priority, int)
                else cast("Priority", priority).value
            )
            _max_retries = max_retries
            _timeout = timeout
            _queue = queue
            _idempotency_key = idempotency_key

            @property
            def __name__(self) -> str:
                """Return task name."""
                return self._task_name

            def __call__(self, *args: Any, **kwargs: Any) -> Any:
                """Direct function call."""
                return func(*args, **kwargs)

            @classmethod
            def signature(cls, *args: Any, **kwargs: Any) -> JobProtocol:
                """Create task signature without executing.

                Returns:
                    JobProtocol instance ready to be enqueued
                """
                return JobProtocol(
                    id="",
                    name=cls._task_name,
                    args=args,
                    kwargs=kwargs,
                    priority=cls._priority,
                    max_retries=cls._max_retries,
                    idempotency_key=cls._idempotency_key,
                    timeout=cls._timeout,
                )

            @classmethod
            def s(cls, *args: Any, **kwargs: Any) -> JobProtocol:
                """Shorthand for signature().

                Returns:
                    JobProtocol instance ready to be enqueued
                """
                return cls.signature(*args, **kwargs)

            @classmethod
            async def delay(cls, *args: Any, **kwargs: Any) -> Any:
                """Enqueue task for execution (simplified interface)."""
                # This requires a global queue or manager to be set
                # For now, we raise to encourage explicit apply_async or provider usage

                # Try to get provider from context or global if implemented,
                # but for now we follow the existing pattern
                raise NotImplementedError(
                    "Use TaskProvider.enqueue_job() or apply_async(queue, ...)",
                )

            @classmethod
            async def apply_async(
                cls,
                queue: TaskQueueProtocol,
                *args: Any,
                priority: int | None = None,
                max_retries: int | None = None,
                timeout: float | None = None,
                idempotency_key: str | None = None,
                **kwargs: Any,
            ) -> JobProtocol:
                """Enqueue task for asynchronous execution."""
                from lexigram.tasks.models import JobProtocol

                job = JobProtocol(
                    id="",
                    name=cls._task_name,
                    args=args,
                    kwargs=kwargs,
                    priority=priority if priority is not None else cls._priority,
                    max_retries=(
                        max_retries if max_retries is not None else cls._max_retries
                    ),
                    timeout=timeout if timeout is not None else cls._timeout,
                    idempotency_key=idempotency_key
                    if idempotency_key is not None
                    else cls._idempotency_key,
                )

                await queue.enqueue(job)

                return job

        return TaskFunction()

    return decorator


def scheduled(
    cron: str,
    name: str | None = None,
    priority: Priority | int = Priority.NORMAL,
    max_retries: int = 3,
    timeout: float | None = None,
) -> Callable[[Callable[..., Any]], Any]:
    """Decorator to define a scheduled task.

    Args:
        cron: Cron expression (e.g., "0 9 * * *")
        name: Task name
        priority: Task priority
        max_retries: Maximum retry attempts
        timeout: Execution timeout

    Returns:
        Decorated task function with scheduling metadata
    """

    def decorator(func: Callable[..., Any]) -> Any:
        # First wrap it as a task
        task_wrapper = task(
            name=name,
            priority=priority,
            max_retries=max_retries,
            timeout=timeout,
        )(func)

        # Add scheduling metadata
        task_wrapper._cron = cron
        return task_wrapper

    return decorator


__all__ = ["scheduled", "task"]
