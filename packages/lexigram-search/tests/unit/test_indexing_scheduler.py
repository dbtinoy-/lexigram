"""Tests for IndexingScheduler."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.search.exceptions import SchedulerError
from lexigram.search.indexing.batch import BatchStats
from lexigram.search.indexing.scheduler import (
    IndexingJob,
    IndexingScheduler,
    ScheduleConfig,
    SchedulerStats,
    scheduler_context,
)


class TestScheduleConfig:
    """Tests for ScheduleConfig dataclass."""

    def test_default_config(self) -> None:
        """Verify default schedule config values."""
        config = ScheduleConfig()
        assert config.interval_seconds == 3600
        assert config.batch_size == 1000
        assert config.max_concurrent_jobs == 3
        assert config.retry_attempts == 3
        assert config.retry_delay == 60.0
        assert config.enabled is True
        assert config.start_immediately is False


class TestSchedulerStats:
    """Tests for SchedulerStats dataclass."""

    def test_default_stats(self) -> None:
        """Verify default scheduler stats."""
        stats = SchedulerStats()
        assert stats.total_jobs == 0
        assert stats.active_jobs == 0
        assert stats.completed_jobs == 0
        assert stats.failed_jobs == 0
        assert stats.total_documents_processed == 0
        assert stats.start_time is None
        assert stats.uptime_seconds is None


class TestIndexingScheduler:
    """Tests for IndexingScheduler."""

    @pytest.fixture
    def mock_engine(self) -> MagicMock:
        engine = MagicMock()
        return engine

    @pytest.fixture
    def scheduler(self, mock_engine: MagicMock) -> IndexingScheduler:
        return IndexingScheduler(engine=mock_engine)

    @pytest.fixture
    def sample_job(self) -> IndexingJob:
        return IndexingJob(
            name="test_job",
            index="test_index",
            data_source=lambda: [{"id": "1", "name": "test"}],
        )

    def test_add_job(self, scheduler: IndexingScheduler, sample_job: IndexingJob) -> None:
        """Verify add_job adds a job."""
        scheduler.add_job(sample_job)
        assert "test_job" in scheduler.jobs
        assert scheduler._stats.total_jobs == 1

    def test_add_duplicate_job_raises(self, scheduler: IndexingScheduler, sample_job: IndexingJob) -> None:
        """Verify duplicate job name raises SchedulerError."""
        scheduler.add_job(sample_job)
        with pytest.raises(SchedulerError, match="JobProtocol 'test_job' already exists"):
            scheduler.add_job(sample_job)

    def test_add_job_at_capacity(self, scheduler: IndexingScheduler) -> None:
        """Verify add_job at capacity logs warning and returns."""
        scheduler._max_pending_jobs = 0
        job = IndexingJob(
            name="overflow",
            index="test",
            data_source=lambda: [],
        )
        scheduler.add_job(job)
        assert "overflow" not in scheduler.jobs

    def test_remove_job(self, scheduler: IndexingScheduler, sample_job: IndexingJob) -> None:
        """Verify remove_job removes a job."""
        scheduler.add_job(sample_job)
        scheduler.remove_job("test_job")
        assert "test_job" not in scheduler.jobs
        assert scheduler._stats.total_jobs == 0

    def test_remove_nonexistent_job_raises(self, scheduler: IndexingScheduler) -> None:
        """Verify removing nonexistent job raises SchedulerError."""
        with pytest.raises(SchedulerError, match="JobProtocol 'nonexistent' not found"):
            scheduler.remove_job("nonexistent")

    def test_update_job_schedule(self, scheduler: IndexingScheduler, sample_job: IndexingJob) -> None:
        """Verify update_job_schedule updates schedule."""
        scheduler.add_job(sample_job)
        new_schedule = ScheduleConfig(interval_seconds=7200)
        scheduler.update_job_schedule("test_job", new_schedule)
        assert scheduler.jobs["test_job"].schedule.interval_seconds == 7200

    def test_update_nonexistent_job_schedule_raises(self, scheduler: IndexingScheduler) -> None:
        """Verify updating nonexistent job schedule raises."""
        with pytest.raises(SchedulerError, match="JobProtocol 'nonexistent' not found"):
            scheduler.update_job_schedule("nonexistent", ScheduleConfig())

    @pytest.mark.asyncio
    async def test_start_stop(self, scheduler: IndexingScheduler) -> None:
        """Verify start and stop lifecycle."""
        await scheduler.start()
        assert scheduler._running is True
        assert scheduler._stats.start_time is not None
        assert scheduler._scheduler_task is not None

        await scheduler.stop()
        assert scheduler._running is False

    @pytest.mark.asyncio
    async def test_start_idempotent(self, scheduler: IndexingScheduler) -> None:
        """Verify calling start multiple times is safe."""
        await scheduler.start()
        task = scheduler._scheduler_task
        await scheduler.start()  # Should not change anything
        assert scheduler._scheduler_task is task

    @pytest.mark.asyncio
    async def test_stop_idempotent(self, scheduler: IndexingScheduler) -> None:
        """Verify calling stop when not running is safe."""
        await scheduler.stop()  # Should not raise

    @pytest.mark.asyncio
    async def test_run_job_now_nonexistent_raises(self, scheduler: IndexingScheduler) -> None:
        """Verify run_job_now for nonexistent job raises."""
        with pytest.raises(SchedulerError, match="JobProtocol 'nonexistent' not found"):
            await scheduler.run_job_now("nonexistent")

    @pytest.mark.asyncio
    async def test_run_job_now_executes(self, scheduler: IndexingScheduler, sample_job: IndexingJob) -> None:
        """Verify run_job_now executes the job."""
        scheduler.add_job(sample_job)
        with patch.object(scheduler, '_execute_job', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = BatchStats()
            result = await scheduler.run_job_now("test_job")
            assert isinstance(result, BatchStats)
            mock_exec.assert_called_once_with(sample_job)

    @pytest.mark.asyncio
    async def test_execute_job_with_data(self, scheduler: IndexingScheduler, mock_engine: MagicMock) -> None:
        """Verify _execute_job processes data and updates stats."""
        mock_engine.index_document = AsyncMock(return_value=True)

        job = IndexingJob(
            name="test_job",
            index="test_index",
            data_source=lambda: [{"id": "1", "name": "test"}, {"id": "2", "name": "test2"}],
        )
        scheduler.add_job(job)

        with patch('lexigram.search.indexing.scheduler.BatchIndexer') as mock_batch:
            mock_instance = MagicMock()
            mock_instance.index_documents = AsyncMock(return_value=BatchStats(
                total_documents=2,
                processed_documents=2,
                successful_operations=2,
            ))
            mock_batch.return_value = mock_instance

            stats = await scheduler._execute_job(job)

            assert stats.processed_documents == 2
            assert scheduler._stats.completed_jobs == 1
            assert scheduler._stats.total_documents_processed == 2

    @pytest.mark.asyncio
    async def test_execute_job_with_transformer(self, scheduler: IndexingScheduler, mock_engine: MagicMock) -> None:
        """Verify _execute_job applies transformer."""
        job = IndexingJob(
            name="test_job",
            index="test_index",
            data_source=lambda: [{"name": "hello"}],
            transformer=lambda docs: [{**d, "name": d["name"].upper()} for d in docs],
        )
        scheduler.add_job(job)

        with patch('lexigram.search.indexing.scheduler.BatchIndexer') as mock_batch:
            mock_instance = MagicMock()
            mock_instance.index_documents = AsyncMock(return_value=BatchStats(
                processed_documents=1,
            ))
            mock_batch.return_value = mock_instance

            await scheduler._execute_job(job)

            # Verify transformer was applied: data_source returns lowercase, transformer uppercases
            data = job.data_source()
            transformed = job.transformer(data)
            assert transformed[0]["name"] == "HELLO"

    @pytest.mark.asyncio
    async def test_execute_job_empty_data(self, scheduler: IndexingScheduler) -> None:
        """Verify _execute_job handles empty data."""
        job = IndexingJob(
            name="empty_job",
            index="test_index",
            data_source=lambda: [],
        )

        stats = await scheduler._execute_job(job)
        assert isinstance(stats, BatchStats)
        assert stats.processed_documents == 0

    @pytest.mark.asyncio
    async def test_execute_job_retry_on_failure(self, scheduler: IndexingScheduler) -> None:
        """Verify _execute_job disables job after retries exhausted."""
        job = IndexingJob(
            name="failing_job",
            index="test_index",
            data_source=lambda: [{"id": "1"}],
            schedule=ScheduleConfig(retry_attempts=0, retry_delay=0.01),
        )

        with patch('lexigram.search.indexing.scheduler.BatchIndexer') as mock_batch:
            mock_instance = MagicMock()
            mock_instance.index_documents = AsyncMock(side_effect=RuntimeError("fail"))
            mock_batch.return_value = mock_instance

            with pytest.raises(RuntimeError):
                await scheduler._execute_job(job)

            assert scheduler._stats.failed_jobs == 1
            assert job.schedule.enabled is False  # retries exhausted

    @pytest.mark.asyncio
    async def test_get_job_status(self, scheduler: IndexingScheduler, sample_job: IndexingJob) -> None:
        """Verify get_job_status returns expected dict."""
        scheduler.add_job(sample_job)
        status = await scheduler.get_job_status("test_job")
        assert status["name"] == "test_job"
        assert status["index"] == "test_index"
        assert status["is_running"] is False
        assert status["last_run"] is None
        assert status["next_run"] is not None

    @pytest.mark.asyncio
    async def test_get_job_status_nonexistent_raises(self, scheduler: IndexingScheduler) -> None:
        """Verify get_job_status for nonexistent job raises."""
        with pytest.raises(SchedulerError, match="JobProtocol 'nonexistent' not found"):
            await scheduler.get_job_status("nonexistent")

    def test_get_scheduler_stats(self, scheduler: IndexingScheduler) -> None:
        """Verify get_scheduler_stats returns stats."""
        stats = scheduler.get_scheduler_stats()
        assert isinstance(stats, SchedulerStats)
        assert stats.uptime_seconds is None  # No start_time yet

    def test_get_scheduler_stats_with_uptime(self, scheduler: IndexingScheduler) -> None:
        """Verify get_scheduler_stats calculates uptime."""
        from datetime import UTC, timezone
        scheduler._stats.start_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        stats = scheduler.get_scheduler_stats()
        assert stats.uptime_seconds is not None
        assert stats.uptime_seconds > 0

    def test_add_job_start_immediately(self, scheduler: IndexingScheduler) -> None:
        """Verify add_job with start_immediately schedules for now."""
        job = IndexingJob(
            name="immediate",
            index="test",
            data_source=lambda: [],
            schedule=ScheduleConfig(start_immediately=True),
        )
        scheduler.add_job(job)
        assert job.next_run is not None

    def test_update_concurrency(self, scheduler: IndexingScheduler) -> None:
        """Verify _update_concurrency updates semaphore."""
        job1 = IndexingJob(
            name="job1",
            index="test",
            data_source=lambda: [],
            schedule=ScheduleConfig(max_concurrent_jobs=5),
        )
        job2 = IndexingJob(
            name="job2",
            index="test",
            data_source=lambda: [],
            schedule=ScheduleConfig(max_concurrent_jobs=3),
        )
        scheduler.add_job(job1)
        scheduler.add_job(job2)
        assert scheduler._semaphore._value == 5  # max of all jobs


class TestSchedulerContext:
    """Tests for scheduler_context."""

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Verify scheduler_context starts and stops the scheduler."""
        mock_scheduler = MagicMock()
        mock_scheduler.start = AsyncMock()
        mock_scheduler.stop = AsyncMock()

        async with scheduler_context(mock_scheduler) as scheduler:
            assert scheduler is mock_scheduler

        mock_scheduler.start.assert_awaited_once()
        mock_scheduler.stop.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_context_manager_stops_on_error(self) -> None:
        """Verify scheduler_context stops even on error."""
        mock_scheduler = MagicMock()
        mock_scheduler.start = AsyncMock()
        mock_scheduler.stop = AsyncMock()

        with pytest.raises(RuntimeError):
            async with scheduler_context(mock_scheduler):
                raise RuntimeError("boom")

        mock_scheduler.start.assert_awaited_once()
        mock_scheduler.stop.assert_awaited_once()
