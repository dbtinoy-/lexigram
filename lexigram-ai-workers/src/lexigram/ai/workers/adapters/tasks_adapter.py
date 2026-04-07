"""Adapter for lexigram-tasks integration (OPTIONAL).

Bridges ``lexigram-ai`` workers with any task queue backend that satisfies
``lexigram.contracts.tasks.TaskQueueProtocol`` / ``lexigram.contracts.tasks.JobProtocol``.

Both ``JobAdapter`` and ``LexigramTasksAdapter`` work with *any* conforming
implementation — including ``lexigram.tasks`` — without importing from that
package directly.  This avoids a cross-extension import while still providing
the adapters for backwards compatibility.

Example::

    q = LexigramTasksAdapter(container.resolve(TaskQueueProtocol))
    container.register(TaskQueueProtocol, q)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from lexigram.contracts.infra.tasks import JobProtocol, JobStatus, TaskQueueError

if TYPE_CHECKING:
    from lexigram.contracts import TaskQueueProtocol
    from lexigram.result import Result

HAS_LEX_TASKS = True  # Contracts are always available.


class JobAdapter:
    """Adapts any ``lexigram.contracts.tasks.JobProtocol``-conforming object to the protocol.

    Passes through all attributes, providing explicit ``JobStatus`` translation
    for callers that store the enum value rather than the string.
    """

    def __init__(self, raw_job: JobProtocol) -> None:
        """Wrap a raw job object.

        Args:
            raw_job: Any object whose attributes satisfy the ``JobProtocol`` protocol.
        """
        self._job = raw_job

    @property
    def id(self) -> str:
        """Unique job identifier."""
        return self._job.id

    @property
    def status(self) -> JobStatus:
        """Current execution status mapped to the contracts ``JobStatus``."""
        raw = self._job.status
        # Handle both StrEnum values and raw strings
        value = raw.value if hasattr(raw, "value") else str(raw)
        try:
            return JobStatus(value)
        except ValueError:
            return JobStatus.PENDING

    @property
    def data(self) -> dict[str, Any]:
        """JobProtocol payload data."""
        return getattr(self._job, "data", {}) or {}

    @property
    def created_at(self) -> datetime:
        """JobProtocol creation timestamp."""
        return getattr(self._job, "created_at", None) or datetime.now(UTC)

    @property
    def updated_at(self) -> datetime | None:
        """Last update timestamp, or ``None``."""
        return getattr(self._job, "updated_at", None)

    async def update_status(
        self,
        status: JobStatus,
        error: str | None = None,
    ) -> None:
        """Update the underlying job's status.

        Both the contracts ``JobStatus`` and the backing implementation are
        ``StrEnum`` types with identical values, so the enum can be passed
        directly without a ``LexigramJobStatus`` import.

        Args:
            status: The new status value.
            error: Optional error message for failed jobs.
        """
        updater = getattr(self._job, "update_status", None)
        if updater:
            await updater(status, error=error)

    async def update_progress(
        self,
        progress: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Forward a progress update if the underlying job supports it.

        Args:
            progress: Completion fraction in ``[0.0, 1.0]``.
            metadata: Optional metadata to attach to the update.
        """
        if hasattr(self._job, "update_progress"):
            await self._job.update_progress(progress, metadata=metadata)


class LexigramTasksAdapter:
    """Implements ``TaskQueueProtocol`` by delegating to any conforming queue backend.

    This adapter bridges ``lexigram-ai`` workers with any
    ``lexigram.contracts.tasks.TaskQueueProtocol`` implementation (including
    ``lexigram.tasks.TaskQueueProtocol``) without importing from that package.

    Example::

        >>> from lexigram.ai.workers.adapters import LexigramTasksAdapter
        >>> queue = LexigramTasksAdapter(container.resolve(TaskQueueProtocol))
        >>> container.register(TaskQueueProtocol, queue)
    """

    def __init__(self, task_queue: TaskQueueProtocol) -> None:
        """Initialise with a concrete task queue.

        Args:
            task_queue: A ``TaskQueueProtocol``-protocol-conforming queue instance,
                resolved from the DI container.
        """
        self._queue = task_queue

    async def enqueue(
        self,
        job_type: str,
        data: dict[str, Any],
        priority: int = 0,
        delay_seconds: int = 0,
    ) -> str:
        """Enqueue a job.

        Adapts legacy ``(job_type, data, priority, delay_seconds)`` calling
        style to the contracts-first ``TaskQueueProtocol.enqueue(task)`` API.
        """
        task_payload = {
            "name": job_type,
            "args": (),
            "kwargs": data,
            "priority": priority,
            "delay_seconds": delay_seconds,
        }
        result: Result[str, TaskQueueError] = await self._queue.enqueue(task_payload)
        if result.is_err():
            error = result.unwrap_err()
            raise RuntimeError(f"Failed to enqueue task '{job_type}': {error}")
        return result.unwrap()

    async def dequeue(
        self,
        queue_name: str,
        timeout: int = 30,
    ) -> JobProtocol | None:
        """Dequeue the next job and wrap it in a ``JobAdapter``.

        Args:
            queue_name: Name of the queue to dequeue from.
            timeout: Long-poll timeout in seconds.

        Returns:
            A ``JobProtocol``-protocol-conforming object, or ``None``.
        """
        raw = await self._queue.dequeue(queue_name, timeout=timeout)  # type: ignore[call-arg]
        if raw is None:
            return None
        return cast("JobProtocol", JobAdapter(raw))

    async def get_job(self, job_id: str) -> JobProtocol | None:
        """Retrieve a job by ID.

        Args:
            job_id: Unique job identifier.

        Returns:
            A ``JobProtocol``-protocol-conforming object, or ``None``.
        """
        raw = await self._queue.get_job(job_id)
        if raw is None:
            return None
        return cast("JobProtocol", JobAdapter(raw))

    async def delete_job(self, job_id: str) -> bool:
        """Delete a job from the queue.

        Args:
            job_id: Unique job identifier.

        Returns:
            ``True`` if the job was deleted.
        """
        return await self._queue.delete_job(job_id)

    async def count(self, queue_name: str, status: JobStatus | None = None) -> int:
        """Count queued jobs.

        Args:
            queue_name: Queue to inspect.
            status: Optional status filter.

        Returns:
            Number of matching jobs.
        """
        return await self._queue.count(queue_name, status=status)
