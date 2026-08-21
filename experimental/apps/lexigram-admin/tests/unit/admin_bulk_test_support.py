"""Self-contained BulkActionManager reference implementation used by admin bulk tests.

The protocol, dataclasses, manager, decorator, and mock data source under
test live here so the feature-area test modules can stay small.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, Generic, List, Optional, Protocol, TypeVar

import pytest

T = TypeVar("T")


class IBulkDataSource(Protocol[T]):
    """Protocol for data sources that support bulk operations."""

    async def bulk_update(
        self,
        ids: list[Any],
        updates: dict[str, Any],
    ) -> int:
        ...

    async def fetch_by_ids(self, ids: list[Any]) -> list[T]:
        ...

    async def create_snapshot(self, ids: list[Any]) -> str:
        ...

    async def restore_snapshot(self, snapshot_id: str) -> int:
        ...


@dataclass
class BulkEditField:
    """Field configuration for bulk editing."""

    name: str
    label: str
    field_type: str = "text"
    options: Optional[list[tuple[Any, str]]] = None
    required: bool = False
    validation: Optional[Callable[[Any], bool]] = None
    help_text: Optional[str] = None


@dataclass
class BulkAssignConfig:
    """Configuration for bulk assign operations."""

    field_name: str
    label: str
    options: list[tuple[Any, str]]
    allow_null: bool = False
    confirm_message: Optional[str] = None


@dataclass
class BulkActionResult:
    """Result of a bulk action operation."""

    success: bool
    affected_count: int = 0
    errors: list[str] = field(default_factory=list)
    snapshot_id: Optional[str] = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BulkActionSnapshot:
    """Snapshot of records before bulk action."""

    snapshot_id: str
    action_name: str
    record_ids: list[Any]
    timestamp: datetime
    user_id: Optional[Any] = None
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

    def increment(self, count: int = 1):
        """Increment progress counter."""
        self.current += count

    def add_error(self, error: str):
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


# Simple in-memory cache for testing
class SimpleCache:
    def __init__(self):
        self.store: dict[str, Any] = {}

    async def get(self, key: str) -> Optional[Any]:
        return self.store.get(key)

    async def set(self, key: str, value: Any, ttl: int = 300):
        self.store[key] = value


class BulkActionManager(Generic[T]):
    """Manager for advanced bulk operations on data tables."""

    def __init__(
        self,
        data_source: IBulkDataSource[T],
        cache: Optional[Any] = None,
    ):
        self.data_source = data_source
        self.cache = cache or SimpleCache()
        self._custom_actions: dict[str, Callable] = {}
        self._snapshots: dict[str, BulkActionSnapshot] = {}

    async def bulk_edit(
        self,
        ids: list[Any],
        updates: dict[str, Any],
        create_snapshot: bool = True,
        batch_size: int = 100,
    ) -> BulkActionResult:
        """Update multiple records with new field values."""
        start_time = datetime.now()
        snapshot_id = None

        try:
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

            return BulkActionResult(
                success=True,
                affected_count=total_updated,
                snapshot_id=snapshot_id,
                duration_ms=duration,
                metadata={"updates": updates, "batch_size": batch_size},
            )

        except (ConnectionError, RuntimeError, ValueError, TypeError, AttributeError) as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            return BulkActionResult(
                success=False,
                errors=[str(e)],
                duration_ms=duration,
            )

    async def bulk_assign(
        self,
        ids: list[Any],
        field_name: str,
        value: Any,
        create_snapshot: bool = True,
    ) -> BulkActionResult:
        """Assign a value to a specific field for multiple records."""
        return await self.bulk_edit(
            ids=ids,
            updates={field_name: value},
            create_snapshot=create_snapshot,
        )

    def register_action(
        self,
        name: str,
        handler: Callable[[list[Any]], BulkActionResult],
    ):
        """Register a custom bulk action."""
        self._custom_actions[name] = handler

    async def execute_action(
        self,
        action_name: str,
        ids: list[Any],
    ) -> BulkActionResult:
        """Execute a registered custom bulk action."""
        if action_name not in self._custom_actions:
            return BulkActionResult(
                success=False,
                errors=[f"Unknown action: {action_name}"],
            )

        try:
            handler = self._custom_actions[action_name]
            result = await handler(ids)
            return result
        except (ConnectionError, RuntimeError, ValueError, TypeError, AttributeError) as e:
            return BulkActionResult(
                success=False,
                errors=[str(e)],
            )

    async def get_preview(
        self,
        ids: List[Any],
        limit: int = 5,
    ) -> List[T]:
        """Get preview of records that will be affected."""
        preview_ids = ids[:limit]
        return await self.data_source.fetch_by_ids(preview_ids)

    def get_confirmation_message(
        self,
        action_name: str,
        count: int,
        preview: Optional[List[T]] = None,
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
        ids: List[Any],
        handler: Callable[[Any, BulkActionProgress], None],
        batch_size: int = 10,
    ) -> BulkActionResult:
        """Execute bulk action with progress tracking."""
        start_time = datetime.now()
        progress = BulkActionProgress(total=len(ids))

        progress_key = f"bulk_progress_{id(progress)}"
        await self.cache.set(progress_key, progress.to_dict(), ttl=300)

        try:
            for i, record_id in enumerate(ids):
                try:
                    await handler(record_id, progress)
                    progress.increment()
                except (ConnectionError, RuntimeError, ValueError, TypeError, AttributeError) as e:
                    progress.add_error(f"Error processing {record_id}: {e}")

                if i % batch_size == 0:
                    await self.cache.set(progress_key, progress.to_dict(), ttl=300)
                    await asyncio.sleep(0)

            await self.cache.set(progress_key, progress.to_dict(), ttl=300)

            duration = (datetime.now() - start_time).total_seconds() * 1000

            return BulkActionResult(
                success=len(progress.errors) == 0,
                affected_count=progress.current,
                errors=progress.errors,
                duration_ms=duration,
                metadata={"progress_key": progress_key},
            )

        except (ConnectionError, RuntimeError, ValueError, TypeError, AttributeError) as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            return BulkActionResult(
                success=False,
                errors=[str(e)],
                duration_ms=duration,
            )

    async def get_progress(self, progress_key: str) -> Optional[Dict[str, Any]]:
        """Get current progress of a bulk action."""
        return await self.cache.get(progress_key)

    async def undo(self, snapshot_id: str) -> BulkActionResult:
        """Undo a previous bulk action by restoring from snapshot."""
        if snapshot_id not in self._snapshots:
            return BulkActionResult(
                success=False,
                errors=[f"Snapshot not found: {snapshot_id}"],
            )

        try:
            count = await self.data_source.restore_snapshot(snapshot_id)
            snapshot = self._snapshots.pop(snapshot_id)

            return BulkActionResult(
                success=True,
                affected_count=count,
                metadata={
                    "action_name": snapshot.action_name,
                    "timestamp": snapshot.timestamp.isoformat(),
                },
            )

        except (ConnectionError, RuntimeError, ValueError, TypeError, AttributeError) as e:
            return BulkActionResult(
                success=False,
                errors=[str(e)],
            )

    def get_recent_snapshots(self, limit: int = 10) -> List[BulkActionSnapshot]:
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
    icon: Optional[str] = None,
    confirm: bool = True,
    danger: bool = False,
):
    """Decorator to register a custom bulk action."""

    def decorator(func: Callable):
        func._bulk_action_meta = {
            "name": name,
            "label": label,
            "icon": icon,
            "confirm": confirm,
            "danger": danger,
        }
        return func

    return decorator


# -----------------------------------------------------------------------------
# Mock Data Source
# -----------------------------------------------------------------------------


class MockDataSource(IBulkDataSource):
    """Mock data source for testing."""

    def __init__(self):
        self.records: Dict[int, Dict[str, Any]] = {
            1: {"id": 1, "name": "Post 1", "status": "draft", "owner_id": 10},
            2: {"id": 2, "name": "Post 2", "status": "published", "owner_id": 10},
            3: {"id": 3, "name": "Post 3", "status": "draft", "owner_id": 20},
            4: {"id": 4, "name": "Post 4", "status": "archived", "owner_id": 20},
            5: {"id": 5, "name": "Post 5", "status": "draft", "owner_id": 30},
        }
        self.snapshots: Dict[str, Dict[int, Dict[str, Any]]] = {}

    async def bulk_update(self, ids: List[Any], updates: Dict[str, Any]) -> int:
        """Update multiple records."""
        count = 0
        for record_id in ids:
            if record_id in self.records:
                self.records[record_id].update(updates)
                count += 1
        return count

    async def fetch_by_ids(self, ids: List[Any]) -> List[Dict[str, Any]]:
        """Fetch records by IDs."""
        return list(map(lambda rid: self.records[rid], filter(lambda rid: rid in self.records, ids)))

    async def create_snapshot(self, ids: List[Any]) -> str:
        """Create a snapshot for undo."""
        snapshot_id = f"snap_{len(self.snapshots) + 1}"
        snapshot = {rid: self.records[rid].copy() for rid in ids if rid in self.records}
        self.snapshots[snapshot_id] = snapshot
        return snapshot_id

    async def restore_snapshot(self, snapshot_id: str) -> int:
        """Restore from a snapshot."""
        if snapshot_id not in self.snapshots:
            raise ValueError(f"Snapshot not found: {snapshot_id}")

        snapshot = self.snapshots[snapshot_id]
        for rid, data in snapshot.items():
            self.records[rid] = data.copy()

        return len(snapshot)


# -----------------------------------------------------------------------------
# Tests: Bulk Edit
# -----------------------------------------------------------------------------


