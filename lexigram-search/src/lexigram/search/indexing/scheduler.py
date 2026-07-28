"""Indexing Scheduler for Automated Operations"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from lexigram.logging import get_logger
from lexigram.primitives import clock as ambient_clock
from lexigram.search.engine import SearchEngine
from lexigram.search.exceptions import SchedulerError
from lexigram.search.indexing.batch import (
    BatchIndexer,
    BatchStats,
)

logger = get_logger(__name__)


@dataclass
class ScheduleConfig:
    """Indexing schedule configuration"""

    interval_seconds: int = 3600  # 1 hour
    batch_size: int = 1000
    max_concurrent_jobs: int = 3
    retry_attempts: int = 3
    retry_delay: float = 60.0
    enabled: bool = True
    start_immediately: bool = False


@dataclass
class IndexingJob:
    """Indexing job definition"""

    name: str
    index: str
    data_source: Callable[[], list[dict[str, Any]]]
    transformer: Callable[[list[dict[str, Any]]], list[dict[str, Any]]] | None = None
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    last_run: datetime | None = None
    next_run: datetime | None = None
    is_running: bool = False
    stats: BatchStats | None = None


@dataclass
class SchedulerStats:
    """Scheduler statistics"""

    total_jobs: int = 0
    active_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    total_documents_processed: int = 0
    start_time: datetime | None = None
    uptime_seconds: float | None = None


class IndexingScheduler:
    """Schedules and manages automated indexing operations"""

    def __init__(self, engine: SearchEngine, max_pending_jobs: int = 100):
        self.engine = engine
        self.jobs: dict[str, IndexingJob] = {}
        self._scheduler_task: asyncio.Task | None = None
        self._running = False
        self._stats = SchedulerStats()
        self._semaphore = asyncio.Semaphore(3)  # Default concurrency
        self._max_pending_jobs = max_pending_jobs

    def add_job(self, job: IndexingJob) -> None:
        """Add an indexing job"""
        if job.name in self.jobs:
            raise SchedulerError(f"JobProtocol '{job.name}' already exists")

        if len(self.jobs) >= self._max_pending_jobs:
            logger.warning(
                "Pending job queue is at capacity (%d). Dropping job '%s'.",
                self._max_pending_jobs,
                job.name,
            )
            return

        # Set initial next run time
        if job.schedule.start_immediately:
            job.next_run = ambient_clock.now()
        else:
            job.next_run = ambient_clock.now() + timedelta(
                seconds=job.schedule.interval_seconds,
            )

        self.jobs[job.name] = job
        self._stats.total_jobs += 1
        self._update_concurrency()

    def remove_job(self, job_name: str) -> None:
        """Remove an indexing job"""
        if job_name not in self.jobs:
            raise SchedulerError(f"JobProtocol '{job_name}' not found")

        del self.jobs[job_name]
        self._stats.total_jobs -= 1
        self._update_concurrency()

    def update_job_schedule(self, job_name: str, schedule: ScheduleConfig) -> None:
        """Update job schedule"""
        if job_name not in self.jobs:
            raise SchedulerError(f"JobProtocol '{job_name}' not found")

        job = self.jobs[job_name]
        job.schedule = schedule

        # Recalculate next run
        if job.last_run:
            job.next_run = job.last_run + timedelta(seconds=schedule.interval_seconds)
        else:
            job.next_run = ambient_clock.now() + timedelta(
                seconds=schedule.interval_seconds,
            )

    async def start(self) -> None:
        """Start the scheduler"""
        if self._running:
            return

        self._running = True
        self._stats.start_time = ambient_clock.now()

        # Start scheduler task
        self._scheduler_task = asyncio.create_task(self._run_scheduler())

        logger.info("Indexing scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler"""
        if not self._running:
            return

        self._running = False

        # Cancel scheduler task
        if self._scheduler_task:
            self._scheduler_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._scheduler_task

        logger.info("Indexing scheduler stopped")

    async def run_job_now(self, job_name: str) -> BatchStats:
        """Run a job immediately"""
        if job_name not in self.jobs:
            raise SchedulerError(f"JobProtocol '{job_name}' not found")

        job = self.jobs[job_name]

        async with self._semaphore:
            return await self._execute_job(job)

    async def get_job_status(self, job_name: str) -> dict[str, Any]:
        """Get job status"""
        if job_name not in self.jobs:
            raise SchedulerError(f"JobProtocol '{job_name}' not found")

        job = self.jobs[job_name]
        return {
            "name": job.name,
            "index": job.index,
            "is_running": job.is_running,
            "last_run": job.last_run.isoformat() if job.last_run else None,
            "next_run": job.next_run.isoformat() if job.next_run else None,
            "stats": job.stats.__dict__ if job.stats else None,
            "schedule": {
                "interval_seconds": job.schedule.interval_seconds,
                "enabled": job.schedule.enabled,
                "batch_size": job.schedule.batch_size,
            },
        }

    def get_scheduler_stats(self) -> SchedulerStats:
        """Get scheduler statistics"""
        if self._stats.start_time:
            self._stats.uptime_seconds = (
                ambient_clock.now() - self._stats.start_time
            ).total_seconds()

        return self._stats

    async def _run_scheduler(self) -> None:
        """Main scheduler loop"""
        while self._running:
            try:
                # Find jobs that need to run
                now = ambient_clock.now()
                jobs_to_run = []

                for job in self.jobs.values():
                    if (
                        job.schedule.enabled
                        and not job.is_running
                        and job.next_run
                        and now >= job.next_run
                    ):
                        jobs_to_run.append(job)

                # Run jobs concurrently (limited by semaphore)
                if jobs_to_run:
                    tasks = list(map(self._execute_job, jobs_to_run))
                    await asyncio.gather(*tasks, return_exceptions=True)

                # Wait before next check
                await asyncio.sleep(10)  # Check every 10 seconds

            except Exception as e:  # noqa: BLE001 — scheduler loop must not crash on transient errors
                logger.exception("Scheduler error", error=str(e))
                await asyncio.sleep(60)  # Wait a minute on error

    async def _execute_job(self, job: IndexingJob) -> BatchStats:
        """Execute a single indexing job"""
        job.is_running = True
        job.last_run = ambient_clock.now()

        try:
            # Get data from source
            data = job.data_source()
            if not data:
                logger.info("JobProtocol '%s': No data to index", job.name)
                return BatchStats()

            # Apply transformation if provided
            if job.transformer:
                data = job.transformer(data)

            # Create batch indexer
            from lexigram.search.indexing.batch import BatchConfig

            indexer = BatchIndexer(
                self.engine, config=BatchConfig(batch_size=job.schedule.batch_size)
            )

            # Execute indexing
            stats = await indexer.index_documents(job.index, data)

            # Update job stats
            job.stats = stats
            self._stats.completed_jobs += 1
            self._stats.total_documents_processed += stats.processed_documents

            # Schedule next run
            job.next_run = ambient_clock.now() + timedelta(
                seconds=job.schedule.interval_seconds,
            )

            logger.info(
                "JobProtocol '%s': Completed - %s documents",
                job.name,
                stats.processed_documents,
            )

            return stats

        except Exception as e:  # noqa: BLE001 — job executor must log any failure before re-raising
            logger.exception("JobProtocol '%s' failed", job.name, error=str(e))
            self._stats.failed_jobs += 1

            # Retry logic
            if job.schedule.retry_attempts > 0:
                job.schedule.retry_attempts -= 1
                # Schedule retry with delay
                job.next_run = ambient_clock.now() + timedelta(
                    seconds=job.schedule.retry_delay,
                )
            else:
                # JobProtocol permanently failed
                job.schedule.enabled = False

            raise

        finally:
            job.is_running = False

    def _update_concurrency(self) -> None:
        """Update concurrency semaphore based on job configurations"""
        max_concurrent = max(
            (job.schedule.max_concurrent_jobs for job in self.jobs.values()),
            default=3,
        )
        self._semaphore = asyncio.Semaphore(max_concurrent)


@asynccontextmanager
async def scheduler_context(scheduler: IndexingScheduler) -> Any:
    """Context manager for scheduler operations"""
    try:
        await scheduler.start()
        yield scheduler
    finally:
        await scheduler.stop()


__all__ = [
    "IndexingJob",
    "IndexingScheduler",
    "ScheduleConfig",
    "SchedulerStats",
    "scheduler_context",
]
