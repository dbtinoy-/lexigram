"""Type definitions for AI Workers — enums and dataclasses used across subpackages."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from lexigram.contracts import JobProtocol


# ── DLQ types ────────────────────────────────────────────────────────


class FailureCategory(StrEnum):
    """Categories of failures."""

    TRANSIENT = "transient"
    PERMANENT = "permanent"
    THROTTLED = "throttled"
    INVALID_INPUT = "invalid_input"
    UNKNOWN = "unknown"


class DLQAction(StrEnum):
    """Actions for DLQ items."""

    RETRY = "retry"
    ARCHIVE = "archive"
    DELETE = "delete"
    NOTIFY = "notify"


@dataclass
class DLQItem:
    """Item in the dead letter queue."""

    job_id: str
    original_job: JobProtocol
    failure_count: int
    first_failure: datetime
    last_failure: datetime
    last_error: str
    failure_category: FailureCategory = FailureCategory.UNKNOWN
    retry_count: int = 0
    max_retries: int = 5
    next_retry: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def can_retry(self) -> bool:
        """Check if item can be retried."""
        if self.retry_count >= self.max_retries:
            return False
        if self.failure_category == FailureCategory.PERMANENT:
            return False
        return not (self.next_retry and datetime.now(UTC) < self.next_retry)

    def calculate_backoff(self, base_delay: int = 60) -> int:
        """Calculate exponential backoff delay in seconds."""
        return min(base_delay * (2**self.retry_count), 3600)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "job_id": self.job_id,
            "failure_count": self.failure_count,
            "first_failure": self.first_failure.isoformat(),
            "last_failure": self.last_failure.isoformat(),
            "last_error": self.last_error,
            "failure_category": self.failure_category.value,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "next_retry": self.next_retry.isoformat() if self.next_retry else None,
            "can_retry": self.can_retry(),
            "metadata": self.metadata,
        }


@dataclass
class DLQStats:
    """Statistics for DLQ."""

    total_items: int = 0
    by_category: dict[str, int] = field(default_factory=dict)
    retried_count: int = 0
    archived_count: int = 0
    deleted_count: int = 0
    permanent_failures: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_items": self.total_items,
            "by_category": self.by_category,
            "retried_count": self.retried_count,
            "archived_count": self.archived_count,
            "deleted_count": self.deleted_count,
            "permanent_failures": self.permanent_failures,
        }


# ── Maintenance types ────────────────────────────────────────────────


class MaintenanceTaskType(StrEnum):
    """Types of maintenance tasks."""

    INDEX_OPTIMIZATION = "index_optimization"
    CACHE_CLEANUP = "cache_cleanup"
    DOCUMENT_CLEANUP = "document_cleanup"
    METRICS_ROLLUP = "metrics_rollup"
    HEALTH_CHECK = "health_check"


class MaintenanceStatus(StrEnum):
    """Maintenance task status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class MaintenanceTask:
    """Configuration for a maintenance task."""

    name: str
    task_type: MaintenanceTaskType
    handler: Callable[[], Any]
    schedule_cron: str | None = None
    interval_seconds: int | None = None
    enabled: bool = True
    timeout: float = 300.0

    last_run: datetime | None = None
    last_status: MaintenanceStatus = MaintenanceStatus.PENDING
    last_error: str | None = None
    run_count: int = 0

    def should_run(self) -> bool:
        """Check if task should run based on schedule."""
        if not self.enabled:
            return False
        if self.last_run is None:
            return True
        if self.interval_seconds:
            elapsed = (datetime.now(UTC) - self.last_run).total_seconds()
            return elapsed >= self.interval_seconds
        return False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "task_type": self.task_type.value,
            "schedule_cron": self.schedule_cron,
            "interval_seconds": self.interval_seconds,
            "enabled": self.enabled,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_status": self.last_status.value,
            "last_error": self.last_error,
            "run_count": self.run_count,
        }


@dataclass
class MaintenanceResult:
    """Result of a maintenance task execution."""

    task_name: str
    task_type: MaintenanceTaskType
    status: MaintenanceStatus
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    items_processed: int = 0
    items_deleted: int = 0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success(
        cls,
        task_name: str,
        task_type: MaintenanceTaskType,
        started_at: datetime,
        items_processed: int = 0,
        items_deleted: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> MaintenanceResult:
        """Create successful result."""
        now = datetime.now(UTC)
        return cls(
            task_name=task_name,
            task_type=task_type,
            status=MaintenanceStatus.COMPLETED,
            started_at=started_at,
            completed_at=now,
            duration_seconds=(now - started_at).total_seconds(),
            items_processed=items_processed,
            items_deleted=items_deleted,
            metadata=metadata or {},
        )

    @classmethod
    def failure(
        cls,
        task_name: str,
        task_type: MaintenanceTaskType,
        started_at: datetime,
        error: str,
    ) -> MaintenanceResult:
        """Create failed result."""
        now = datetime.now(UTC)
        return cls(
            task_name=task_name,
            task_type=task_type,
            status=MaintenanceStatus.FAILED,
            started_at=started_at,
            completed_at=now,
            duration_seconds=(now - started_at).total_seconds(),
            error=error,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_name": self.task_name,
            "task_type": self.task_type.value,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "items_processed": self.items_processed,
            "items_deleted": self.items_deleted,
            "error": self.error,
            "metadata": self.metadata,
        }


__all__ = [
    "DLQAction",
    "DLQItem",
    "DLQStats",
    "FailureCategory",
    "MaintenanceResult",
    "MaintenanceStatus",
    "MaintenanceTask",
    "MaintenanceTaskType",
]
