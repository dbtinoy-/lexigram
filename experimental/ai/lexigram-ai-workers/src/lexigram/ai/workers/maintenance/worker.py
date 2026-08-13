"""
Maintenance worker for periodic cleanup and optimization.

Handles scheduled maintenance tasks including:
- Vector store index optimization
- Embedding cache cleanup (TTL-based)
- Old document cleanup
- Metrics aggregation and rollup
- Health check monitoring
"""

from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from lexigram.ai.workers.types import (
    MaintenanceResult,
    MaintenanceStatus,
    MaintenanceTask,
    MaintenanceTaskType,
)
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from lexigram.contracts import VectorStoreProtocol

logger = get_logger(__name__)


class MaintenanceWorker:
    """
    Background worker for scheduled maintenance tasks.

    Executes periodic maintenance operations including:
    - Vector store index optimization
    - Cache cleanup and TTL enforcement
    - Old document cleanup
    - Metrics aggregation

    Example:
        ```python
        from lexigram.ai.workers import MaintenanceWorker
        from lexigram.contracts import VectorStoreProtocol

        # Setup — resolve via the DI container
        vector_store = container.resolve(VectorStoreProtocol)

        worker = MaintenanceWorker(
            vector_store=vector_store,
            worker_id="maintenance",
        )

        # Register maintenance tasks
        worker.register_task(
            name="optimize_indexes",
            task_type=MaintenanceTaskType.INDEX_OPTIMIZATION,
            handler=lambda: vector_store.optimize_indexes(),
            interval_seconds=3600,  # Every hour
        )

        worker.register_task(
            name="cleanup_old_docs",
            task_type=MaintenanceTaskType.DOCUMENT_CLEANUP,
            handler=lambda: cleanup_documents(days=30),
            schedule_cron="0 2 * * *",  # 2 AM daily
        )

        # Start worker
        await worker.start()

        # Get statistics
        stats = worker.get_stats()
        logger.info(f"Tasks run: {stats['total_runs']}")

        # Stop worker
        await worker.stop()
        ```
    """

    def __init__(
        self,
        vector_store: VectorStoreProtocol | None = None,
        worker_id: str = "maintenance",
        check_interval: int = 60,  # Check every 60 seconds
    ):
        """
        Initialize maintenance worker.

        Args:
            vector_store: Optional vector store for index optimization
            worker_id: Unique worker identifier
            check_interval: Interval in seconds to check for tasks to run
        """
        self.vector_store = vector_store
        self.worker_id = worker_id
        self.check_interval = check_interval

        # Task registry
        self._tasks: dict[str, MaintenanceTask] = {}
        self._tasks_lock = asyncio.Lock()

        # Execution history
        self._history: list[MaintenanceResult] = []
        self._history_lock = asyncio.Lock()
        self._max_history = 1000  # Keep last 1000 results

        # Worker state
        self._running = False
        self._worker_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the maintenance worker."""
        if self._running:
            logger.warning("Worker %s already running", self.worker_id)
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._maintenance_loop())

        logger.info(
            "Started maintenance worker",
            worker_id=self.worker_id,
            check_interval=self.check_interval,
            registered_tasks=len(self._tasks),
        )

    async def stop(self) -> None:
        """Stop the maintenance worker."""
        if not self._running:
            return

        self._running = False

        if self._worker_task:
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task

        logger.info("Stopped maintenance worker", worker_id=self.worker_id)

    def register_task(
        self,
        name: str,
        task_type: MaintenanceTaskType,
        handler: Callable[[], Any],
        schedule_cron: str | None = None,
        interval_seconds: int | None = None,
        enabled: bool = True,
        timeout: float = 300.0,
    ) -> None:
        """
        Register a maintenance task.

        Args:
            name: Unique task name
            task_type: Type of maintenance task
            handler: Async or sync callable to execute
            schedule_cron: Cron expression for scheduling
            interval_seconds: Simple interval in seconds
            enabled: Whether task is enabled
            timeout: Task timeout in seconds
        """
        if not schedule_cron and not interval_seconds:
            msg = "Must provide either schedule_cron or interval_seconds"
            raise ValueError(msg)

        task = MaintenanceTask(
            name=name,
            task_type=task_type,
            handler=handler,
            schedule_cron=schedule_cron,
            interval_seconds=interval_seconds,
            enabled=enabled,
            timeout=timeout,
        )

        self._tasks[name] = task

        logger.info(
            "Registered maintenance task",
            task_name=name,
            task_type=task_type.value,
            interval_seconds=interval_seconds,
            cron=schedule_cron,
        )

    def unregister_task(self, name: str) -> None:
        """Unregister a maintenance task."""
        if name in self._tasks:
            del self._tasks[name]
            logger.info("Unregistered maintenance task", task_name=name)

    def enable_task(self, name: str) -> None:
        """Enable a maintenance task."""
        if name in self._tasks:
            self._tasks[name].enabled = True
            logger.info("Enabled maintenance task", task_name=name)

    def disable_task(self, name: str) -> None:
        """Disable a maintenance task."""
        if name in self._tasks:
            self._tasks[name].enabled = False
            logger.info("Disabled maintenance task", task_name=name)

    async def run_task_now(self, name: str) -> MaintenanceResult:
        """
        Run a specific maintenance task immediately.

        Args:
            name: Task name to run

        Returns:
            Maintenance result
        """
        async with self._tasks_lock:
            if name not in self._tasks:
                msg = f"Task not found: {name}"
                raise ValueError(msg)

            task = self._tasks[name]

        logger.info("Running maintenance task manually", task_name=name)
        return await self._execute_task(task)

    async def _maintenance_loop(self) -> None:
        """Main maintenance loop that checks and runs tasks."""
        while self._running:
            try:
                # Check all tasks for execution
                async with self._tasks_lock:
                    tasks_to_run = [
                        task for task in self._tasks.values() if task.should_run()
                    ]

                # Execute tasks that need to run
                for task in tasks_to_run:
                    try:
                        result = await self._execute_task(task)

                        # Store result
                        await self._store_result(result)

                        # Update task
                        async with self._tasks_lock:
                            task.last_run = result.completed_at
                            task.last_status = result.status
                            task.last_error = result.error
                            task.run_count += 1

                    except Exception as e:
                        logger.exception(
                            "Error executing maintenance task",
                            task_name=task.name,
                            error=str(e),
                        )

                # Wait for next check
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(
                    "Error in maintenance loop",
                    error=str(e),
                )
                await asyncio.sleep(self.check_interval)

    async def _execute_task(self, task: MaintenanceTask) -> MaintenanceResult:
        """Execute a single maintenance task."""
        started_at = datetime.now(UTC)

        logger.info(
            "Executing maintenance task",
            task_name=task.name,
            task_type=task.task_type.value,
        )

        try:
            # Execute with timeout
            if asyncio.iscoroutinefunction(task.handler):
                result = await asyncio.wait_for(
                    task.handler(),
                    timeout=task.timeout,
                )
            else:
                # Run sync handler in thread pool
                result = await asyncio.wait_for(
                    asyncio.to_thread(task.handler),
                    timeout=task.timeout,
                )

            # Parse result
            items_processed = 0
            items_deleted = 0
            metadata = {}

            if isinstance(result, dict):
                items_processed = result.get("items_processed", 0)
                items_deleted = result.get("items_deleted", 0)
                metadata = result.get("metadata", {})
            elif isinstance(result, int):
                items_processed = result

            maintenance_result = MaintenanceResult.success(
                task_name=task.name,
                task_type=task.task_type,
                started_at=started_at,
                items_processed=items_processed,
                items_deleted=items_deleted,
                metadata=metadata,
            )

            logger.info(
                "Maintenance task completed",
                task_name=task.name,
                duration=f"{maintenance_result.duration_seconds:.2f}s",
                items_processed=items_processed,
                items_deleted=items_deleted,
            )

        except TimeoutError:
            error_msg = f"Task timed out after {task.timeout}s"
            logger.exception(
                "Maintenance task timed out",
                timeout=task.timeout,
            )

            return MaintenanceResult.failure(
                task_name=task.name,
                task_type=task.task_type,
                started_at=started_at,
                error=error_msg,
            )

        except Exception as e:
            error_msg = str(e)
            logger.exception(
                "Maintenance task failed",
                task_name=task.name,
                error=error_msg,
            )

            return MaintenanceResult.failure(
                task_name=task.name,
                task_type=task.task_type,
                started_at=started_at,
                error=error_msg,
            )
        else:
            return maintenance_result

    async def _store_result(self, result: MaintenanceResult) -> None:
        """Store maintenance result in history."""
        async with self._history_lock:
            self._history.append(result)

            # Trim history if needed
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history :]

    def get_stats(self) -> dict[str, Any]:
        """Get worker statistics."""
        total_runs = sum(task.run_count for task in self._tasks.values())
        successful_runs = sum(
            1
            for result in self._history
            if result.status == MaintenanceStatus.COMPLETED
        )
        failed_runs = sum(
            1 for result in self._history if result.status == MaintenanceStatus.FAILED
        )

        return {
            "worker_id": self.worker_id,
            "running": self._running,
            "registered_tasks": len(self._tasks),
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "history_size": len(self._history),
        }

    def get_task_status(self, name: str) -> dict[str, Any] | None:
        """Get status of a specific task."""
        if name not in self._tasks:
            return None

        return self._tasks[name].to_dict()

    def get_all_tasks(self) -> list[dict[str, Any]]:
        """Get status of all registered tasks."""
        return [task.to_dict() for task in self._tasks.values()]

    def get_recent_results(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent maintenance results."""
        return [result.to_dict() for result in self._history[-limit:]]

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report the health of this worker.

        Args:
            timeout: Unused; present for protocol conformance.

        Returns:
            HEALTHY when the worker is running, UNHEALTHY otherwise.
        """
        status = HealthStatus.HEALTHY if self._running else HealthStatus.UNHEALTHY
        stats = self.get_stats()
        return HealthCheckResult(
            component=f"worker.maintenance.{self.worker_id}",
            status=status,
            details=stats,
        )

    # Built-in maintenance handlers

    async def optimize_vector_indexes(self) -> dict[str, Any]:
        """
        Optimize vector store indexes.

        This is a built-in handler for index optimization.
        """
        if not self.vector_store:
            msg = "Vector store not configured"
            raise ValueError(msg)

        logger.info("Starting vector index optimization")

        # Call vector store optimization if supported
        if hasattr(self.vector_store, "optimize_indexes"):
            result = await self.vector_store.optimize_indexes()
            return {
                "items_processed": result.get("collections_optimized", 0),
                "metadata": result,
            }

        logger.warning("Vector store does not support index optimization")
        return {"items_processed": 0}

    async def cleanup_old_embeddings_cache(
        self,
        max_age_days: int = 30,
    ) -> dict[str, Any]:
        """
        Clean up old embeddings from cache.

        This is a built-in handler for cache cleanup.

        Args:
            max_age_days: Maximum age in days for cached embeddings
        """
        # This is a placeholder - actual implementation would need
        # access to the embedding cache
        logger.info(
            "Cleaning up embeddings cache",
            max_age_days=max_age_days,
        )

        # Placeholder return
        return {
            "items_deleted": 0,
            "metadata": {"max_age_days": max_age_days},
        }

    async def aggregate_metrics(self) -> dict[str, Any]:
        """
        Aggregate and rollup metrics.

        This is a built-in handler for metrics aggregation.
        """
        logger.info("Aggregating metrics")

        # Placeholder - actual implementation would aggregate
        # metrics from the metrics collector
        return {
            "items_processed": 0,
            "metadata": {"aggregation_type": "hourly"},
        }
