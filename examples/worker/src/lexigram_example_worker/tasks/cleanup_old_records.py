"""Scheduled cleanup task handler.

Demonstrates the ``@scheduled`` decorator for cron-driven periodic tasks.
The task deletes expired records from an in-memory store (replace with a
real repository in production).

Patterns demonstrated:
- ``@scheduled`` decorator with cron expression
- Constructor injection for the repository dependency
- ``Result[T, E]`` for the cleanup operation outcome
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Protocol

from lexigram.contracts.exceptions.domain import DomainError
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result
from lexigram.tasks.decorators import scheduled

logger = get_logger(__name__)

# Records older than this threshold are considered expired.
_DEFAULT_RETENTION_DAYS = 30


# ---------------------------------------------------------------------------
# Repository protocol (contract boundary — inject, never import concrete impl)
# ---------------------------------------------------------------------------


class RecordRepositoryProtocol(Protocol):
    """Minimal async repository contract for purgeable records.

    Real implementations may wrap SQLAlchemy or any other persistence layer.
    Tests inject a ``FakeRecordRepository`` that tracks deleted IDs.
    """

    async def delete_older_than(self, cutoff: datetime) -> int:
        """Delete all records with a timestamp older than *cutoff*.

        Args:
            cutoff: UTC datetime threshold — records at-or-before are removed.

        Returns:
            Number of records deleted.
        """
        ...


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CleanupResult:
    """Outcome of a successful cleanup run.

    Attributes:
        deleted_count: Number of records removed from the store.
        cutoff: The UTC datetime used as the expiry boundary.
    """

    deleted_count: int
    cutoff: datetime


# ---------------------------------------------------------------------------
# Handler (class-based, constructor-injected)
# ---------------------------------------------------------------------------


class CleanupOldRecordsHandler:
    """Deletes expired records via the injected repository.

    Accepts a :class:`RecordRepositoryProtocol` via constructor injection so
    the concrete persistence layer is swappable without touching this class.

    Args:
        repository: Async record repository implementation.
        retention_days: Records older than this many days are considered
            expired.  Defaults to :data:`_DEFAULT_RETENTION_DAYS`.
    """

    def __init__(
        self,
        repository: RecordRepositoryProtocol,
        retention_days: int = _DEFAULT_RETENTION_DAYS,
    ) -> None:
        self._repository = repository
        self._retention_days = retention_days

    async def execute(self) -> Result[CleanupResult, DomainError]:
        """Run the cleanup pass and return a summary result.

        Returns:
            ``Ok(CleanupResult)`` with the deletion count on success;
            ``Err(DomainError)`` if the repository raises.
        """
        cutoff = datetime.now(UTC) - timedelta(days=self._retention_days)

        logger.info(
            "cleanup_old_records.started",
            cutoff=cutoff.isoformat(),
            retention_days=self._retention_days,
        )

        try:
            deleted_count = await self._repository.delete_older_than(cutoff)
        except Exception as exc:
            error_msg = f"Repository error during cleanup: {exc}"
            logger.error("cleanup_old_records.failed", error=error_msg)
            return Err(DomainError(error_msg))

        logger.info(
            "cleanup_old_records.completed",
            deleted_count=deleted_count,
            cutoff=cutoff.isoformat(),
        )
        return Ok(CleanupResult(deleted_count=deleted_count, cutoff=cutoff))


# ---------------------------------------------------------------------------
# Scheduled task function (cron-driven)
#
# The cron expression is set via WorkerConfig.cleanup_cron and passed to
# WorkerProvider.  Here we define the task at module level with a sensible
# default so it is self-documenting.
# ---------------------------------------------------------------------------


@scheduled(cron="0 3 * * *", name="cleanup_old_records", max_retries=2)
async def cleanup_old_records_task() -> None:
    """Nightly cleanup task — deletes records older than the retention window.

    This function is the ``@scheduled`` entry-point registered with the
    :class:`~lexigram.tasks.scheduling.scheduler.TaskScheduler`.  The actual
    work is delegated to an injected :class:`CleanupOldRecordsHandler` resolved
    from the DI container at runtime.

    The ``@scheduled`` decorator makes the task discoverable by the scheduler
    and stores the cron expression as ``cleanup_old_records_task._cron``.
    """
    # The task function body is intentionally minimal — the handler is
    # resolved from the container and injected by WorkerProvider.boot().
    # In a full integration this would call:
    #   handler = await container.resolve(CleanupOldRecordsHandler)
    #   result = await handler.execute()
    logger.info("cleanup_old_records_task.invoked")


__all__ = [
    "CleanupOldRecordsHandler",
    "CleanupResult",
    "RecordRepositoryProtocol",
    "cleanup_old_records_task",
]
