"""Tests for AI workers types."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from lexigram.ai.workers.types import (
    DLQAction,
    DLQItem,
    DLQStats,
    FailureCategory,
    MaintenanceResult,
    MaintenanceStatus,
    MaintenanceTask,
    MaintenanceTaskType,
)


class TestFailureCategory:
    """Test FailureCategory enum."""

    def test_values(self) -> None:
        """Test all failure category values."""
        assert FailureCategory.TRANSIENT.value == "transient"
        assert FailureCategory.PERMANENT.value == "permanent"
        assert FailureCategory.THROTTLED.value == "throttled"
        assert FailureCategory.INVALID_INPUT.value == "invalid_input"
        assert FailureCategory.UNKNOWN.value == "unknown"

    def test_is_str_enum(self) -> None:
        """Test it's a StrEnum."""
        assert isinstance(FailureCategory.TRANSIENT, str)


class TestDLQAction:
    """Test DLQAction enum."""

    def test_values(self) -> None:
        """Test all DLQ action values."""
        assert DLQAction.RETRY.value == "retry"
        assert DLQAction.ARCHIVE.value == "archive"
        assert DLQAction.DELETE.value == "delete"
        assert DLQAction.NOTIFY.value == "notify"


class TestDLQItem:
    """Test DLQItem dataclass."""

    def test_creation(self) -> None:
        """Test DLQItem creation."""
        now = datetime.now(UTC)
        item = DLQItem(
            job_id="job-1",
            original_job=MagicMock(),  # type: ignore[arg-type]
            failure_count=1,
            first_failure=now,
            last_failure=now,
            last_error="Test error",
        )
        assert item.job_id == "job-1"
        assert item.failure_count == 1

    def test_can_retry_true(self) -> None:
        """Test can_retry returns true for retryable item."""
        now = datetime.now(UTC)
        item = DLQItem(
            job_id="job-1",
            original_job=MagicMock(),  # type: ignore[arg-type]
            failure_count=1,
            first_failure=now,
            last_failure=now,
            last_error="Test error",
            retry_count=1,
            max_retries=5,
        )
        assert item.can_retry() is True

    def test_can_retry_max_retries_exceeded(self) -> None:
        """Test can_retry returns false when max retries exceeded."""
        now = datetime.now(UTC)
        item = DLQItem(
            job_id="job-1",
            original_job=MagicMock(),  # type: ignore[arg-type]
            failure_count=5,
            first_failure=now,
            last_failure=now,
            last_error="Test error",
            retry_count=5,
            max_retries=5,
        )
        assert item.can_retry() is False

    def test_can_retry_permanent_failure(self) -> None:
        """Test can_retry returns false for permanent failures."""
        now = datetime.now(UTC)
        item = DLQItem(
            job_id="job-1",
            original_job=MagicMock(),  # type: ignore[arg-type]
            failure_count=1,
            first_failure=now,
            last_failure=now,
            last_error="Test error",
            failure_category=FailureCategory.PERMANENT,
        )
        assert item.can_retry() is False

    def test_calculate_backoff(self) -> None:
        """Test exponential backoff calculation."""
        now = datetime.now(UTC)
        item = DLQItem(
            job_id="job-1",
            original_job=MagicMock(),  # type: ignore[arg-type]
            failure_count=1,
            first_failure=now,
            last_failure=now,
            last_error="Test error",
            retry_count=2,
        )
        assert item.calculate_backoff(60) == 240  # 60 * 2^2

    def test_to_dict(self) -> None:
        """Test to_dict serialization."""
        now = datetime.now(UTC)
        item = DLQItem(
            job_id="job-1",
            original_job=MagicMock(),  # type: ignore[arg-type]
            failure_count=1,
            first_failure=now,
            last_failure=now,
            last_error="Test error",
        )
        d = item.to_dict()
        assert d["job_id"] == "job-1"
        assert d["failure_category"] == "unknown"


class TestDLQStats:
    """Test DLQStats dataclass."""

    def test_creation(self) -> None:
        """Test DLQStats creation."""
        stats = DLQStats(
            total_items=10,
            by_category={"transient": 5, "permanent": 5},
            retried_count=2,
            archived_count=1,
            deleted_count=1,
            permanent_failures=3,
        )
        assert stats.total_items == 10
        assert stats.retried_count == 2


class TestMaintenanceTaskType:
    """Test MaintenanceTaskType enum."""

    def test_values(self) -> None:
        """Test all maintenance task types."""
        assert MaintenanceTaskType.INDEX_OPTIMIZATION.value == "index_optimization"
        assert MaintenanceTaskType.CACHE_CLEANUP.value == "cache_cleanup"
        assert MaintenanceTaskType.DOCUMENT_CLEANUP.value == "document_cleanup"


class TestMaintenanceStatus:
    """Test MaintenanceStatus enum."""

    def test_values(self) -> None:
        """Test all maintenance status values."""
        assert MaintenanceStatus.PENDING.value == "pending"
        assert MaintenanceStatus.RUNNING.value == "running"
        assert MaintenanceStatus.COMPLETED.value == "completed"
        assert MaintenanceStatus.FAILED.value == "failed"
        assert MaintenanceStatus.SKIPPED.value == "skipped"


class TestMaintenanceTask:
    """Test MaintenanceTask dataclass."""

    def test_creation(self) -> None:
        """Test MaintenanceTask creation."""
        def handler():
            pass

        task = MaintenanceTask(
            name="test-task",
            task_type=MaintenanceTaskType.CACHE_CLEANUP,
            handler=handler,
            interval_seconds=3600,
        )
        assert task.name == "test-task"
        assert task.enabled is True

    def test_should_run_disabled(self) -> None:
        """Test should_run returns false when disabled."""
        task = MaintenanceTask(
            name="test",
            task_type=MaintenanceTaskType.HEALTH_CHECK,
            handler=lambda: None,
            enabled=False,
        )
        assert task.should_run() is False


class TestMaintenanceResult:
    """Test MaintenanceResult dataclass."""

    def test_success_factory(self) -> None:
        """Test success factory method."""
        started = datetime.now(UTC)
        result = MaintenanceResult.success(
            task_name="test",
            task_type=MaintenanceTaskType.CACHE_CLEANUP,
            started_at=started,
            items_processed=100,
        )
        assert result.status == MaintenanceStatus.COMPLETED
        assert result.items_processed == 100

    def test_failure_factory(self) -> None:
        """Test failure factory method."""
        started = datetime.now(UTC)
        result = MaintenanceResult.failure(
            task_name="test",
            task_type=MaintenanceTaskType.CACHE_CLEANUP,
            started_at=started,
            error="Something went wrong",
        )
        assert result.status == MaintenanceStatus.FAILED
        assert result.error == "Something went wrong"


class TestAllWorkerTypes:
    """Test all types are exported."""

    def test_all_exports(self) -> None:
        """Test __all__ contains expected types."""
        from lexigram.ai.workers import types

        expected = [
            "DLQAction",
            "DLQItem",
            "DLQStats",
            "FailureCategory",
            "MaintenanceResult",
            "MaintenanceStatus",
            "MaintenanceTask",
            "MaintenanceTaskType",
        ]
        assert sorted(types.__all__) == sorted(expected)