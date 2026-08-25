"""
Dead Letter Queue (DLQ) worker for failed task recovery.

Handles failed task recovery including:
- Retry mechanisms with exponential backoff
- Error classification and routing
- Failure analysis and reporting
- Manual retry triggers
- Permanent failure handling

Uses Dependency Injection - TaskQueueProtocol is injected, not imported.
"""

from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from lexigram.contracts import JobProtocol, TaskQueueProtocol

from lexigram.ai.workers.dlq.classifier import ErrorClassifier
from lexigram.ai.workers.types import (
    DLQItem,
    DLQStats,
    FailureCategory,
)
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Result

logger = get_logger(__name__)


class DeadLetterQueueWorker:
    """
    Worker for handling failed tasks and retry logic.

    Monitors failed jobs and implements intelligent retry strategies
    based on failure categorization.

    Example:
        ```python
        from lexigram.ai.workers import DeadLetterQueueWorker
        from lexigram.contracts.infra.tasks import TaskQueueProtocol

        # Setup
        main_queue = TaskQueueProtocol()
        dlq_queue = TaskQueueProtocol()  # Separate queue for DLQ items

        worker = DeadLetterQueueWorker(
            main_queue=main_queue,
            dlq_queue=dlq_queue,
            worker_id="dlq",
            check_interval=60,  # Check every minute
        )

        # Register error notification handler
        async def notify_on_permanent_failure(item: DLQItem):
            await send_alert(f"Permanent failure: {item.job_id}")

        worker.set_notification_handler(notify_on_permanent_failure)

        # Start worker
        await worker.start()

        # Manually retry a failed job
        await worker.retry_item(job_id="abc123")

        # Get DLQ statistics
        stats = await worker.get_stats()
        logger.info(f"Total failed items: {stats.total_items}")

        # Stop worker
        await worker.stop()
        ```
    """

    def __init__(
        self,
        main_queue: TaskQueueProtocol,
        dlq_queue: TaskQueueProtocol | None = None,
        worker_id: str = "dlq",
        check_interval: int = 60,
        max_retries: int = 5,
        base_backoff: int = 60,
    ):
        """
        Initialize DLQ worker.

        Args:
            main_queue: Main task queue to monitor
            dlq_queue: Optional separate queue for DLQ items
            worker_id: Unique worker identifier
            check_interval: Interval in seconds to check for failed jobs
            max_retries: Maximum retry attempts per job
            base_backoff: Base delay in seconds for exponential backoff
        """
        self.main_queue = main_queue
        self.dlq_queue = dlq_queue or main_queue
        self.worker_id = worker_id
        self.check_interval = check_interval
        self.max_retries = max_retries
        self.base_backoff = base_backoff

        # DLQ storage
        self._items: dict[str, DLQItem] = {}
        self._items_lock = asyncio.Lock()
        self.dead_letter_count = 0

        # Error classifier
        self._classifier = ErrorClassifier()

        # Notification handler
        self._notification_handler: Callable[[DLQItem], Any] | None = None

        # Worker state
        self._running = False
        self._worker_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the DLQ worker."""
        if self._running:
            logger.warning("Worker %s already running", self.worker_id)
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._dlq_loop())

        logger.info(
            "Started DLQ worker",
            worker_id=self.worker_id,
            check_interval=self.check_interval,
            max_retries=self.max_retries,
        )

    async def stop(self) -> None:
        """Stop the DLQ worker."""
        if not self._running:
            return

        self._running = False

        if self._worker_task:
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task

        logger.info("Stopped DLQ worker", worker_id=self.worker_id)

    def set_notification_handler(
        self,
        handler: Callable[[DLQItem], Any],
    ) -> None:
        """
        Set notification handler for permanent failures.

        Args:
            handler: Async callable that receives DLQItem
        """
        self._notification_handler = handler
        logger.info("Set DLQ notification handler")

    async def add_failed_job(self, job: JobProtocol, error: str) -> None:
        """
        Add a failed job to the DLQ.

        Args:
            job: Failed job
            error: Error message
        """
        async with self._items_lock:
            if job.id in self._items:
                # Update existing item
                item = self._items[job.id]
                item.failure_count += 1
                item.last_failure = datetime.now(UTC)
                item.last_error = error
            else:
                # Create new DLQ item
                now = datetime.now(UTC)
                failure_category = self._classifier.classify(error, job)

                item = DLQItem(
                    job_id=job.id,
                    original_job=job,
                    failure_count=1,
                    first_failure=now,
                    last_failure=now,
                    last_error=error,
                    failure_category=failure_category,
                    max_retries=self.max_retries,
                )

                self._items[job.id] = item
                self.dead_letter_count += 1

            logger.info(
                "Added job to DLQ",
                job_id=job.id,
                failure_count=item.failure_count,
                category=item.failure_category.value,
            )

    async def retry_item(self, job_id: str) -> bool:
        """
        Manually retry a DLQ item.

        Args:
            job_id: JobProtocol ID to retry

        Returns:
            True if retry was initiated, False otherwise
        """
        async with self._items_lock:
            if job_id not in self._items:
                logger.warning("JobProtocol not found in DLQ", job_id=job_id)
                return False

            item = self._items[job_id]

            if not item.can_retry():
                logger.warning(
                    "JobProtocol cannot be retried",
                    job_id=job_id,
                    retry_count=item.retry_count,
                    max_retries=item.max_retries,
                )
                return False

            # Retry the job
            await self._retry_job(item)
            return True

    async def remove_item(self, job_id: str) -> bool:
        """
        Remove item from DLQ (permanent deletion).

        Args:
            job_id: JobProtocol ID to remove

        Returns:
            True if removed, False if not found
        """
        async with self._items_lock:
            if job_id in self._items:
                del self._items[job_id]
                logger.info("Removed job from DLQ", job_id=job_id)
                return True
            return False

    async def archive_item(self, job_id: str) -> bool:
        """
        Archive item (mark as permanently failed).

        Args:
            job_id: JobProtocol ID to archive

        Returns:
            True if archived, False if not found
        """
        async with self._items_lock:
            if job_id in self._items:
                item = self._items[job_id]
                item.failure_category = FailureCategory.PERMANENT
                item.metadata["archived"] = True
                item.metadata["archived_at"] = datetime.now(UTC).isoformat()

                logger.info("Archived job in DLQ", job_id=job_id)
                return True
            return False

    async def get_stats(self) -> DLQStats:
        """Get DLQ statistics."""
        async with self._items_lock:
            stats = DLQStats(total_items=len(self._items))

            for item in self._items.values():
                category = item.failure_category.value
                stats.by_category[category] = stats.by_category.get(category, 0) + 1

                if item.retry_count > 0:
                    stats.retried_count += 1

                if item.failure_category == FailureCategory.PERMANENT:
                    stats.permanent_failures += 1

                if item.metadata.get("archived"):
                    stats.archived_count += 1

            return stats

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report the health of this worker.

        Args:
            timeout: Unused; present for protocol conformance.

        Returns:
            HEALTHY when the worker is running, UNHEALTHY otherwise.
        """
        status = HealthStatus.HEALTHY if self._running else HealthStatus.UNHEALTHY
        stats = await self.get_stats()
        return HealthCheckResult(
            component=f"worker.dlq.{self.worker_id}",
            status=status,
            details=stats.to_dict(),
        )

    async def get_items(
        self,
        category: FailureCategory | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get DLQ items.

        Args:
            category: Optional filter by failure category
            limit: Maximum items to return

        Returns:
            List of DLQ items as dictionaries
        """
        async with self._items_lock:
            items = list(self._items.values())

            if category:
                items = list(
                    filter(lambda item: item.failure_category == category, items),
                )

            # Sort by last failure (most recent first)
            items.sort(key=lambda x: x.last_failure, reverse=True)

            return [item.to_dict() for item in items[:limit]]

    async def _dlq_loop(self) -> None:
        """Main DLQ processing loop."""
        while self._running:
            try:
                # Check for items ready to retry
                async with self._items_lock:
                    items_to_retry = [
                        item for item in self._items.values() if item.can_retry()
                    ]

                # Retry eligible items
                for item in items_to_retry:
                    try:
                        await self._retry_job(item)
                    except Exception as e:
                        logger.exception(
                            "Error retrying job",
                            job_id=item.job_id,
                            error=str(e),
                        )

                # Check for permanent failures to notify
                async with self._items_lock:
                    permanent_failures = [
                        item
                        for item in self._items.values()
                        if (
                            item.failure_category == FailureCategory.PERMANENT
                            and not item.metadata.get("notified")
                        )
                    ]

                # Send notifications
                for item in permanent_failures:
                    try:
                        await self._notify_permanent_failure(item)
                        item.metadata["notified"] = True
                    except Exception as e:
                        logger.exception(
                            "Error sending notification",
                            job_id=item.job_id,
                            error=str(e),
                        )

                # Wait for next check
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(
                    "Error in DLQ loop",
                    error=str(e),
                )
                await asyncio.sleep(self.check_interval)

    async def _retry_job(self, item: DLQItem) -> None:
        """Retry a failed job."""
        # Calculate backoff delay
        backoff = item.calculate_backoff(self.base_backoff)
        item.next_retry = datetime.now(UTC) + timedelta(seconds=backoff)
        item.retry_count += 1

        logger.info(
            "Retrying job",
            job_id=item.job_id,
            retry_count=item.retry_count,
            next_retry=item.next_retry.isoformat(),
        )

        # Re-enqueue the job using queue's enqueue(job_type, data, priority) API
        job_name = item.original_job.name
        if job_name is None:
            logger.error("Original job name missing; cannot retry", job_id=item.job_id)
            return

        # Narrow type for mypy: job_name is Optional[str] on JobProtocol, assert non-None
        assert job_name is not None  # noqa: S101  # type-narrowing only; log branch returned above

        priority = (
            item.original_job.priority if item.original_job.priority is not None else 0
        )

        new_job_data: dict[str, Any] = {
            "name": job_name,
            "args": item.original_job.args or [],
            "kwargs": item.original_job.kwargs or {},
            "priority": priority,
            "max_retries": 1,  # Only one retry per DLQ attempt
            "timeout": item.original_job.timeout,
        }

        enqueue_result = await self.dlq_queue.enqueue(
            {
                "name": job_name,
                "args": tuple(item.original_job.args or []),
                "kwargs": new_job_data,
                "priority": priority,
            }
        )
        if isinstance(enqueue_result, Result) and enqueue_result.is_err():
            logger.warning(
                "dlq_retry_enqueue_failed",
                job_id=item.job_id,
                error=str(enqueue_result.unwrap_err()),
            )
            return

        if not item.metadata.get("replayed"):
            item.metadata["replayed"] = True
            self.dead_letter_count -= 1

    async def _notify_permanent_failure(self, item: DLQItem) -> None:
        """Notify about permanent failure."""
        if not self._notification_handler:
            return

        logger.info(
            "Notifying permanent failure",
            job_id=item.job_id,
            error=item.last_error,
        )

        if asyncio.iscoroutinefunction(self._notification_handler):
            await self._notification_handler(item)
        else:
            await asyncio.to_thread(self._notification_handler, item)
