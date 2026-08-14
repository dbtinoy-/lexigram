"""
Advanced Bulk Action Manager for Lexigram Admin.

Provides comprehensive bulk operation support including:
- Bulk editing and assignment
- Custom action registration
- Progress tracking
- Undo functionality via snapshots
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, Protocol, TypeVar

from lexigram.admin.exceptions import AdminError, NotFoundError
from lexigram.contracts.infra.cache import CacheBackendProtocol
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)

T = TypeVar("T")


class IBulkDataSource(Protocol[T]):
    """Protocol for data sources that support bulk operations."""

    async def bulk_update(
        self,
        ids: list[Any],
        updates: dict[str, Any],
    ) -> int:
        """Update multiple records."""
        ...

    async def fetch_by_ids(self, ids: list[Any]) -> list[T]:
        """Fetch records by IDs."""
        ...

    async def create_snapshot(self, ids: list[Any]) -> str:
        """Create a snapshot for undo."""
        ...

    async def restore_snapshot(self, snapshot_id: str) -> int:
        """Restore from a snapshot."""
        ...


@dataclass
class BulkEditField:
    """Field configuration for bulk editing."""

    name: str
    label: str
    field_type: str = "text"
    options: list[tuple[Any, str]] | None = None
    required: bool = False
    validation: Callable[[Any], bool] | None = None
    help_text: str | None = None


@dataclass
class BulkAssignConfig:
    """Configuration for bulk assign operations."""

    field_name: str
    label: str
    options: list[tuple[Any, str]]
    allow_null: bool = False
    confirm_message: str | None = None


@dataclass
class BulkActionResult:
    """Payload of a completed bulk action operation.

    Always carried inside ``Ok[BulkActionResult, AdminError]``.  Per-item
    failures are accumulated in ``errors``; a non-empty ``errors`` list does
    NOT mean the overall operation failed — only an ``Err`` return does.
    """

    affected_count: int = 0
    errors: list[str] = field(default_factory=list)
    snapshot_id: str | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BulkActionSnapshot:
    """Snapshot of records before bulk action."""

    snapshot_id: str
    action_name: str
    record_ids: list[Any]
    timestamp: datetime
    user_id: Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BulkActionProgress:
    """Track progress of long-running bulk actions."""

    def __init__(self, total: int):
        self.total = total
        self.current = 0
        self.errors: list[str] = []
        self.start_time = datetime.now()

    @property
    def percentage(self) -> float:
        """Get completion percentage."""
        if self.total == 0:
            return 100.0
        return (self.current / self.total) * 100

    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        delta = datetime.now() - self.start_time
        return delta.total_seconds() * 1000

    def increment(self, count: int = 1) -> Any:
        """Increment progress counter."""
        self.current += count

    def add_error(self, error: str) -> Any:
        """Add an error message."""
        self.errors.append(error)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total": self.total,
            "current": self.current,
            "percentage": self.percentage,
            "elapsed_ms": self.elapsed_ms,
            "errors": self.errors,
        }


class BulkActionManager(Generic[T]):
    """Manager for advanced bulk operations on data tables."""

    def __init__(
        self,
        data_source: IBulkDataSource[T],
        cache: CacheBackendProtocol | None = None,
    ):
        self.data_source = data_source
        self._cache_backend = cache
        self._custom_actions: dict[str, Callable] = {}
        self._snapshots: dict[str, BulkActionSnapshot] = {}

    async def bulk_edit(
        self,
        ids: list[Any],
        updates: dict[str, Any],
        create_snapshot: bool = True,
        batch_size: int = 100,
    ) -> Result[BulkActionResult, AdminError]:
        """Update multiple records with new field values."""
        start_time = datetime.now()
        snapshot_id = None

        if create_snapshot:
            snapshot_id = await self.data_source.create_snapshot(ids)
            self._snapshots[snapshot_id] = BulkActionSnapshot(
                snapshot_id=snapshot_id,
                action_name="bulk_edit",
                record_ids=ids,
                timestamp=datetime.now(),
            )

        total_updated = 0
        progress = BulkActionProgress(total=len(ids))

        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i : i + batch_size]
            count = await self.data_source.bulk_update(batch_ids, updates)
            total_updated += count
            progress.increment(len(batch_ids))
            await asyncio.sleep(0)

        duration = (datetime.now() - start_time).total_seconds() * 1000

        return Ok(
            BulkActionResult(
                affected_count=total_updated,
                snapshot_id=snapshot_id,
                duration_ms=duration,
                metadata={"updates": updates, "batch_size": batch_size},
            )
        )

    async def bulk_assign(
        self,
        ids: list[Any],
        field_name: str,
        value: Any,
        create_snapshot: bool = True,
    ) -> Result[BulkActionResult, AdminError]:
        """Assign a value to a specific field for multiple records."""
        return await self.bulk_edit(
            ids=ids,
            updates={field_name: value},
            create_snapshot=create_snapshot,
        )

    def register_action(
        self,
        name: str,
        handler: Callable[[list[Any]], Result[BulkActionResult, AdminError]],
    ) -> None:
        """Register a custom bulk action."""
        self._custom_actions[name] = handler

    async def execute_action(
        self,
        action_name: str,
        ids: list[Any],
    ) -> Result[BulkActionResult, AdminError]:
        """Execute a registered custom bulk action."""
        if action_name not in self._custom_actions:
            return Err(NotFoundError(f"Unknown action: {action_name}"))  # type: ignore[arg-type]

        handler = self._custom_actions[action_name]
        return await handler(ids)

    async def get_preview(
        self,
        ids: list[Any],
        limit: int = 5,
    ) -> list[T]:
        """Get preview of records that will be affected."""
        preview_ids = ids[:limit]
        return await self.data_source.fetch_by_ids(preview_ids)

    def get_confirmation_message(
        self,
        action_name: str,
        count: int,
        preview: list[T] | None = None,
    ) -> str:
        """Generate confirmation message for bulk action."""
        msg = f"Are you sure you want to {action_name} {count} record(s)?"

        if preview:
            msg += "\n\nThis will affect:"
            for record in preview:
                msg += f"\n- {record}"

        return msg

    async def execute_with_progress(
        self,
        ids: list[Any],
        handler: Callable[[Any, BulkActionProgress], Any],
        batch_size: int = 10,
    ) -> Result[BulkActionResult, AdminError]:
        """Execute bulk action with progress tracking."""
        start_time = datetime.now()
        progress = BulkActionProgress(total=len(ids))

        progress_key = f"bulk_progress_{id(progress)}"
        if self._cache_backend is not None:
            await self._cache_backend.set(progress_key, progress.to_dict(), 300)

        for i, record_id in enumerate(ids):
            try:
                handler_result = handler(record_id, progress)
                if handler_result is not None:
                    if hasattr(handler_result, "__await__"):
                        await handler_result
                progress.increment()
            except (
                ValueError,
                ConnectionError,
                TimeoutError,
                OSError,
                KeyError,
            ) as e:
                progress.add_error(f"Error processing {record_id}: {e}")

            if i % batch_size == 0:
                if self._cache_backend is not None:
                    await self._cache_backend.set(progress_key, progress.to_dict(), 300)
                await asyncio.sleep(0)

        if self._cache_backend is not None:
            await self._cache_backend.set(progress_key, progress.to_dict(), 300)

        duration = (datetime.now() - start_time).total_seconds() * 1000

        return Ok(
            BulkActionResult(
                affected_count=progress.current,
                errors=progress.errors,
                duration_ms=duration,
                metadata={"progress_key": progress_key},
            )
        )

    async def get_progress(self, progress_key: str) -> dict[str, Any] | None:
        """Get current progress of a bulk action."""
        if self._cache_backend is None:
            return None
        res = await self._cache_backend.get(progress_key)
        return res.unwrap() if res.is_ok() else None

    async def undo(self, snapshot_id: str) -> Result[BulkActionResult, AdminError]:
        """Undo a previous bulk action by restoring from snapshot."""
        if snapshot_id not in self._snapshots:
            return Err(NotFoundError(f"Snapshot not found: {snapshot_id}"))  # type: ignore[arg-type]

        count = await self.data_source.restore_snapshot(snapshot_id)
        snapshot = self._snapshots.pop(snapshot_id)

        return Ok(
            BulkActionResult(
                affected_count=count,
                metadata={
                    "action_name": snapshot.action_name,
                    "timestamp": snapshot.timestamp.isoformat(),
                },
            )
        )

    def get_recent_snapshots(self, limit: int = 10) -> list[BulkActionSnapshot]:
        """Get recent snapshots available for undo."""
        snapshots = sorted(
            self._snapshots.values(),
            key=lambda s: s.timestamp,
            reverse=True,
        )
        return snapshots[:limit]


def bulk_action(
    name: str,
    label: str,
    icon: str | None = None,
    confirm: bool = True,
    danger: bool = False,
) -> Any:
    """Decorator to register a custom bulk action."""

    def decorator(func: Callable) -> Any:
        func._bulk_action_meta = {  # type: ignore[attr-defined]
            "name": name,
            "label": label,
            "icon": icon,
            "confirm": confirm,
            "danger": danger,
        }
        return func

    return decorator
