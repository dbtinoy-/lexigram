"""Unit tests for lexigram.ai.workers.dlq — Dead Letter Queue worker."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.workers.dlq import (
    DeadLetterQueueWorker,
    ErrorClassifier,
)
from lexigram.ai.workers.types import (
    DLQItem,
    DLQStats,
    FailureCategory,
)
from lexigram.contracts import JobProtocol, TaskQueueProtocol


class DummyJob(JobProtocol):
    def __init__(self, job_id: str, name: str | None = "dummy_job", priority: int = 0):
        self.id = job_id
        self.name = name
        self.args = []
        self.kwargs = {}
        self.priority = priority
        self.timeout = 300

    def get_id(self) -> str:
        return self.id


class TestErrorClassifier:
    def test_classify_permanent(self) -> None:
        job = DummyJob("1")
        assert ErrorClassifier.classify("User not found", job) == FailureCategory.PERMANENT
        assert ErrorClassifier.classify("syntax error in input", job) == FailureCategory.PERMANENT

    def test_classify_throttled(self) -> None:
        job = DummyJob("1")
        assert ErrorClassifier.classify("Rate limit exceeded", job) == FailureCategory.THROTTLED

    def test_classify_invalid_input(self) -> None:
        job = DummyJob("1")
        assert ErrorClassifier.classify("validation error failed", job) == FailureCategory.INVALID_INPUT

    def test_classify_transient(self) -> None:
        job = DummyJob("1")
        assert ErrorClassifier.classify("connection timeout", job) == FailureCategory.TRANSIENT
        assert ErrorClassifier.classify("error 503 unavailable", job) == FailureCategory.TRANSIENT

    def test_classify_unknown(self) -> None:
        job = DummyJob("1")
        assert ErrorClassifier.classify("weird obscure error", job) == FailureCategory.UNKNOWN


class TestDLQItem:
    def test_can_retry_max_retries(self) -> None:
        item = DLQItem(
            job_id="1", original_job=DummyJob("1"), failure_count=1,
            first_failure=datetime.now(UTC), last_failure=datetime.now(UTC),
            last_error="error", retry_count=5, max_retries=5
        )
        assert item.can_retry() is False

    def test_can_retry_permanent_failure(self) -> None:
        item = DLQItem(
            job_id="1", original_job=DummyJob("1"), failure_count=1,
            first_failure=datetime.now(UTC), last_failure=datetime.now(UTC),
            last_error="error", failure_category=FailureCategory.PERMANENT
        )
        assert item.can_retry() is False

    def test_can_retry_next_retry_future(self) -> None:
        item = DLQItem(
            job_id="1", original_job=DummyJob("1"), failure_count=1,
            first_failure=datetime.now(UTC), last_failure=datetime.now(UTC),
            last_error="error", next_retry=datetime.now(UTC) + timedelta(minutes=10)
        )
        assert item.can_retry() is False

    def test_can_retry_true(self) -> None:
        item = DLQItem(
            job_id="1", original_job=DummyJob("1"), failure_count=1,
            first_failure=datetime.now(UTC), last_failure=datetime.now(UTC),
            last_error="error", next_retry=datetime.now(UTC) - timedelta(minutes=10)
        )
        assert item.can_retry() is True

    def test_calculate_backoff(self) -> None:
        item = DLQItem(
            job_id="1", original_job=DummyJob("1"), failure_count=1,
            first_failure=datetime.now(UTC), last_failure=datetime.now(UTC),
            last_error="error", retry_count=2
        )
        assert item.calculate_backoff(base_delay=10) == 40  # 10 * 2^2


class TestDeadLetterQueueWorker:
    @pytest.fixture
    def queue(self) -> MagicMock:
        q = MagicMock(spec=TaskQueueProtocol)
        q.enqueue = AsyncMock()
        return q

    @pytest.fixture
    def worker(self, queue: MagicMock) -> DeadLetterQueueWorker:
        return DeadLetterQueueWorker(main_queue=queue, check_interval=1)

    @pytest.mark.asyncio
    async def test_add_failed_job_new(self, worker: DeadLetterQueueWorker) -> None:
        job = DummyJob("job-1")
        await worker.add_failed_job(job, "timeout error")
        assert "job-1" in worker._items
        item = worker._items["job-1"]
        assert item.failure_count == 1
        assert item.last_error == "timeout error"
        assert item.failure_category == FailureCategory.TRANSIENT

    @pytest.mark.asyncio
    async def test_add_failed_job_existing(self, worker: DeadLetterQueueWorker) -> None:
        job = DummyJob("job-1")
        await worker.add_failed_job(job, "timeout error")
        await worker.add_failed_job(job, "another error")
        item = worker._items["job-1"]
        assert item.failure_count == 2
        assert item.last_error == "another error"

    @pytest.mark.asyncio
    async def test_retry_item_success(self, worker: DeadLetterQueueWorker, queue: MagicMock) -> None:
        job = DummyJob("job-1", name="test_job")
        await worker.add_failed_job(job, "timeout error")
        
        # Manually force item to be retriable now
        worker._items["job-1"].next_retry = datetime.now(UTC) - timedelta(minutes=1)
        
        result = await worker.retry_item("job-1")
        assert result is True
        queue.enqueue.assert_awaited_once()
        assert worker._items["job-1"].retry_count == 1

    @pytest.mark.asyncio
    async def test_retry_item_not_found(self, worker: DeadLetterQueueWorker) -> None:
        result = await worker.retry_item("missing")
        assert result is False

    @pytest.mark.asyncio
    async def test_retry_item_cannot_retry(self, worker: DeadLetterQueueWorker) -> None:
        job = DummyJob("job-1", name="test_job")
        await worker.add_failed_job(job, "not found error") # Permanent -> cannot retry
        result = await worker.retry_item("job-1")
        assert result is False

    @pytest.mark.asyncio
    async def test_archive_item(self, worker: DeadLetterQueueWorker) -> None:
        job = DummyJob("job-1")
        await worker.add_failed_job(job, "timeout error")
        assert await worker.archive_item("job-1") is True
        item = worker._items["job-1"]
        assert item.failure_category == FailureCategory.PERMANENT
        assert item.metadata.get("archived") is True

    @pytest.mark.asyncio
    async def test_remove_item(self, worker: DeadLetterQueueWorker) -> None:
        job = DummyJob("job-1")
        await worker.add_failed_job(job, "timeout error")
        assert await worker.remove_item("job-1") is True
        assert "job-1" not in worker._items

    @pytest.mark.asyncio
    async def test_get_stats(self, worker: DeadLetterQueueWorker) -> None:
        job1 = DummyJob("1")
        job2 = DummyJob("2")
        await worker.add_failed_job(job1, "timeout") # TRANSIENT
        await worker.add_failed_job(job2, "invalid dict") # PERMANENT
        
        stats = await worker.get_stats()
        assert stats.total_items == 2
        assert stats.permanent_failures == 1
        assert stats.by_category[FailureCategory.TRANSIENT.value] == 1
        assert stats.by_category[FailureCategory.PERMANENT.value] == 1

    @pytest.mark.asyncio
    async def test_get_items(self, worker: DeadLetterQueueWorker) -> None:
        job1 = DummyJob("1")
        job2 = DummyJob("2")
        await worker.add_failed_job(job1, "timeout")
        
        # Ensure distinct last_failure times
        await asyncio.sleep(0.01)
        await worker.add_failed_job(job2, "invalid")
        
        items = await worker.get_items()
        assert len(items) == 2
        # items should be sorted by last_failure descending
        assert items[0]["job_id"] == "2"
        assert items[1]["job_id"] == "1"

    @pytest.mark.asyncio
    async def test_start_stop(self, worker: DeadLetterQueueWorker) -> None:
        await worker.start()
        assert worker._running is True
        assert worker._worker_task is not None
        await worker.stop()
        assert worker._running is False

    @pytest.mark.asyncio
    async def test_notification_handler(self, worker: DeadLetterQueueWorker) -> None:
        job = DummyJob("job-1")
        await worker.add_failed_job(job, "invalid syntax") # PERMANENT
        
        handler = AsyncMock()
        worker.set_notification_handler(handler)
        
        # Manually invoke loop once
        worker._running = True
        worker._worker_task = asyncio.create_task(worker._dlq_loop())
        await asyncio.sleep(0.1)
        await worker.stop()
        
        handler.assert_awaited_once()
