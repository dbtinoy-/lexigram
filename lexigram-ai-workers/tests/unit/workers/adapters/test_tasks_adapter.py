"""Tests for tasks adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.workers.adapters.tasks_adapter import (
    JobAdapter,
    LexigramTasksAdapter,
)
from lexigram.contracts.infra.tasks import JobProtocol, JobStatus


class TestJobAdapter:
    """Test JobAdapter class."""

    @pytest.fixture
    def mock_job(self) -> MagicMock:
        """Create a mock job."""
        job = MagicMock()
        job.id = "job-123"
        job.status = JobStatus.PENDING
        job.data = {"key": "value"}
        job.created_at = datetime.now(UTC)
        job.updated_at = datetime.now(UTC)
        job.update_status = AsyncMock()
        return job

    def test_id_property(self, mock_job: MagicMock) -> None:
        """Test id property returns job id."""
        adapter = JobAdapter(mock_job)
        assert adapter.id == "job-123"

    def test_status_property(self, mock_job: MagicMock) -> None:
        """Test status property returns job status."""
        adapter = JobAdapter(mock_job)
        assert adapter.status == JobStatus.PENDING

    def test_status_property_string_value(self) -> None:
        """Test status property handles string values."""
        mock_job = MagicMock()
        mock_job.id = "job-123"
        mock_job.status = "completed"
        mock_job.data = {}
        mock_job.created_at = datetime.now(UTC)
        mock_job.updated_at = None

        adapter = JobAdapter(mock_job)
        assert adapter.status == JobStatus.COMPLETED

    def test_status_property_invalid_value(self) -> None:
        """Test status property handles invalid values."""
        mock_job = MagicMock()
        mock_job.id = "job-123"
        mock_job.status = "invalid_status"
        mock_job.data = {}
        mock_job.created_at = datetime.now(UTC)
        mock_job.updated_at = None

        adapter = JobAdapter(mock_job)
        assert adapter.status == JobStatus.PENDING

    def test_data_property(self, mock_job: MagicMock) -> None:
        """Test data property returns job data."""
        adapter = JobAdapter(mock_job)
        assert adapter.data == {"key": "value"}

    def test_data_property_none(self) -> None:
        """Test data property returns empty dict when None."""
        mock_job = MagicMock()
        mock_job.id = "job-123"
        mock_job.status = JobStatus.PENDING
        mock_job.data = None
        mock_job.created_at = datetime.now(UTC)

        adapter = JobAdapter(mock_job)
        assert adapter.data == {}

    def test_created_at_property(self, mock_job: MagicMock) -> None:
        """Test created_at property."""
        adapter = JobAdapter(mock_job)
        assert adapter.created_at is not None

    def test_updated_at_property(self, mock_job: MagicMock) -> None:
        """Test updated_at property."""
        adapter = JobAdapter(mock_job)
        assert adapter.updated_at is not None

    def test_updated_at_property_none(self) -> None:
        """Test updated_at property returns None when not set."""
        mock_job = MagicMock()
        mock_job.id = "job-123"
        mock_job.status = JobStatus.PENDING
        mock_job.data = {}
        mock_job.created_at = datetime.now(UTC)
        mock_job.updated_at = None

        adapter = JobAdapter(mock_job)
        assert adapter.updated_at is None

    @pytest.mark.asyncio
    async def test_update_status(self, mock_job: MagicMock) -> None:
        """Test update_status calls underlying job."""
        adapter = JobAdapter(mock_job)
        await adapter.update_status(JobStatus.COMPLETED)
        mock_job.update_status.assert_awaited_once_with(JobStatus.COMPLETED, error=None)

    @pytest.mark.asyncio
    async def test_update_status_with_error(self, mock_job: MagicMock) -> None:
        """Test update_status with error message."""
        adapter = JobAdapter(mock_job)
        await adapter.update_status(JobStatus.FAILED, error="Something went wrong")
        mock_job.update_status.assert_awaited_once_with(
            JobStatus.FAILED, error="Something went wrong"
        )

    @pytest.mark.asyncio
    async def test_update_progress_calls_when_supported(self, mock_job: MagicMock) -> None:
        """Test update_progress calls underlying job when supported."""
        mock_job.update_progress = AsyncMock()
        adapter = JobAdapter(mock_job)
        await adapter.update_progress(0.5, metadata={"step": 1})
        mock_job.update_progress.assert_awaited_once_with(0.5, metadata={"step": 1})

    @pytest.mark.asyncio
    async def test_update_progress_silent_when_not_supported(self, mock_job: MagicMock) -> None:
        """Test update_progress does nothing when not supported."""
        del mock_job.update_progress
        adapter = JobAdapter(mock_job)
        await adapter.update_progress(0.5)
        # Should not raise


class TestLexigramTasksAdapter:
    """Test LexigramTasksAdapter class."""

    @pytest.fixture
    def mock_queue(self) -> MagicMock:
        """Create a mock task queue."""
        queue = MagicMock()
        queue.enqueue = AsyncMock()
        queue.dequeue = AsyncMock()
        queue.get_job = AsyncMock()
        queue.delete_job = AsyncMock()
        queue.count = AsyncMock()
        return queue

    @pytest.fixture
    def adapter(self, mock_queue: MagicMock) -> LexigramTasksAdapter:
        """Create a LexigramTasksAdapter instance."""
        return LexigramTasksAdapter(mock_queue)

    @pytest.mark.asyncio
    async def test_enqueue_success(self, adapter: LexigramTasksAdapter, mock_queue: MagicMock) -> None:
        """Test enqueue succeeds."""
        from lexigram.result import Ok

        mock_queue.enqueue = AsyncMock(return_value=Ok("job-123"))
        result = await adapter.enqueue("test_job", {"key": "value"}, priority=5, delay_seconds=10)
        assert result == "job-123"

    @pytest.mark.asyncio
    async def test_enqueue_failure_raises(self, adapter: LexigramTasksAdapter, mock_queue: MagicMock) -> None:
        """Test enqueue failure raises RuntimeError."""
        from lexigram.contracts.infra.tasks import TaskQueueError
        from lexigram.result import Err

        mock_queue.enqueue = AsyncMock(return_value=Err(TaskQueueError("Queue full")))
        with pytest.raises(RuntimeError, match="Failed to enqueue"):
            await adapter.enqueue("test_job", {})

    @pytest.mark.asyncio
    async def test_dequeue_returns_none(self, adapter: LexigramTasksAdapter, mock_queue: MagicMock) -> None:
        """Test dequeue returns None when queue is empty."""
        mock_queue.dequeue = AsyncMock(return_value=None)
        result = await adapter.dequeue("test_queue")
        assert result is None

    @pytest.mark.asyncio
    async def test_dequeue_returns_adapter(self, adapter: LexigramTasksAdapter, mock_queue: MagicMock) -> None:
        """Test dequeue returns wrapped job."""
        raw_job = MagicMock()
        raw_job.id = "job-123"
        raw_job.status = JobStatus.PENDING
        raw_job.data = {}
        raw_job.created_at = datetime.now(UTC)
        mock_queue.dequeue = AsyncMock(return_value=raw_job)

        result = await adapter.dequeue("test_queue")
        assert result is not None
        assert isinstance(result, JobAdapter)
        assert result.id == "job-123"

    @pytest.mark.asyncio
    async def test_get_job_returns_none(self, adapter: LexigramTasksAdapter, mock_queue: MagicMock) -> None:
        """Test get_job returns None when not found."""
        mock_queue.get_job = AsyncMock(return_value=None)
        result = await adapter.get_job("job-123")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_job_returns_adapter(self, adapter: LexigramTasksAdapter, mock_queue: MagicMock) -> None:
        """Test get_job returns wrapped job."""
        raw_job = MagicMock()
        raw_job.id = "job-123"
        raw_job.status = JobStatus.COMPLETED
        raw_job.data = {}
        raw_job.created_at = datetime.now(UTC)
        mock_queue.get_job = AsyncMock(return_value=raw_job)

        result = await adapter.get_job("job-123")
        assert result is not None
        assert isinstance(result, JobAdapter)

    @pytest.mark.asyncio
    async def test_delete_job(self, adapter: LexigramTasksAdapter, mock_queue: MagicMock) -> None:
        """Test delete_job calls underlying queue."""
        mock_queue.delete_job = AsyncMock(return_value=True)
        result = await adapter.delete_job("job-123")
        assert result is True
        mock_queue.delete_job.assert_awaited_once_with("job-123")

    @pytest.mark.asyncio
    async def test_count(self, adapter: LexigramTasksAdapter, mock_queue: MagicMock) -> None:
        """Test count returns job count."""
        mock_queue.count = AsyncMock(return_value=10)
        result = await adapter.count("test_queue")
        assert result == 10
        mock_queue.count.assert_awaited_once_with("test_queue", status=None)

    @pytest.mark.asyncio
    async def test_count_with_status(self, adapter: LexigramTasksAdapter, mock_queue: MagicMock) -> None:
        """Test count with status filter."""
        mock_queue.count = AsyncMock(return_value=5)
        result = await adapter.count("test_queue", status=JobStatus.PENDING)
        assert result == 5
        mock_queue.count.assert_awaited_once_with("test_queue", status=JobStatus.PENDING)

    @pytest.mark.asyncio
    async def test_get_stats_reports_pending_from_task_count(self, adapter: LexigramTasksAdapter, mock_queue: MagicMock) -> None:
        """Test get_stats reports pending from get_task_count."""
        mock_queue.get_task_count = AsyncMock(return_value=4)
        stats = await adapter.get_stats()
        assert stats is not None
        assert stats["pending"] == 4
        assert stats["processing"] == 0
        mock_queue.get_task_count.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_get_stats_returns_none_without_task_count(self, adapter: LexigramTasksAdapter, mock_queue: MagicMock) -> None:
        """Test get_stats returns None when the queue lacks get_task_count."""
        mock_queue.get_task_count = None
        assert await adapter.get_stats() is None