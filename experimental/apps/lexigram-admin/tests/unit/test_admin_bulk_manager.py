"""
BulkActionManager core actions: bulk edit, bulk assign, custom actions,
the ``bulk_action`` decorator, preview, and confirmation messages.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, Generic, List, Optional, Protocol, TypeVar

import pytest

from admin_bulk_test_support import (
    BulkActionResult,
    BulkAssignConfig,
    BulkEditField,
    IBulkDataSource,
    SimpleCache,
    BulkActionProgress,
    BulkActionSnapshot,
    BulkActionManager,
    bulk_action,
    MockDataSource,
)




@pytest.mark.asyncio
async def test_bulk_edit_basic():
    """Test basic bulk edit operation."""
    data_source = MockDataSource()
    cache = SimpleCache()
    manager = BulkActionManager(data_source, cache)

    # Update status for records 1, 2, 3
    result = await manager.bulk_edit(
        ids=[1, 2, 3],
        updates={"status": "published"},
        create_snapshot=False,
    )

    assert result.success
    assert result.affected_count == 3
    assert result.snapshot_id is None

    # Verify updates
    records = await data_source.fetch_by_ids([1, 2, 3])
    assert all(r["status"] == "published" for r in records)


@pytest.mark.asyncio
async def test_bulk_edit_with_snapshot():
    """Test bulk edit creates snapshot for undo."""
    data_source = MockDataSource()
    manager = BulkActionManager(data_source)

    # Get original values
    original = await data_source.fetch_by_ids([1, 2])
    _original_status = list(map(lambda r: r["status"], original))

    # Bulk edit with snapshot
    result = await manager.bulk_edit(
        ids=[1, 2],
        updates={"status": "archived"},
        create_snapshot=True,
    )

    assert result.success
    assert result.snapshot_id is not None
    assert result.affected_count == 2

    # Verify updates
    records = await data_source.fetch_by_ids([1, 2])
    assert all(r["status"] == "archived" for r in records)

    # Verify snapshot exists
    snapshots = manager.get_recent_snapshots()
    assert len(snapshots) == 1
    assert snapshots[0].snapshot_id == result.snapshot_id


@pytest.mark.asyncio
async def test_bulk_edit_batching():
    """Test bulk edit processes in batches."""
    data_source = MockDataSource()
    manager = BulkActionManager(data_source)

    # Bulk edit with small batch size
    result = await manager.bulk_edit(
        ids=[1, 2, 3, 4, 5],
        updates={"status": "published"},
        batch_size=2,  # Process 2 at a time
        create_snapshot=False,
    )

    assert result.success
    assert result.affected_count == 5
    assert result.metadata["batch_size"] == 2

    # Verify all updated
    records = await data_source.fetch_by_ids([1, 2, 3, 4, 5])
    assert all(r["status"] == "published" for r in records)


@pytest.mark.asyncio
async def test_bulk_edit_error_handling():
    """Test bulk edit handles errors gracefully."""
    data_source = MockDataSource()
    manager = BulkActionManager(data_source)

    # Mock an error
    original_update = data_source.bulk_update

    async def failing_update(*args, **kwargs):
        raise ValueError("Database error")

    data_source.bulk_update = failing_update

    # Attempt bulk edit
    result = await manager.bulk_edit(
        ids=[1, 2, 3],
        updates={"status": "published"},
    )

    assert not result.success
    assert len(result.errors) > 0
    assert "Database error" in result.errors[0]

    # Restore
    data_source.bulk_update = original_update


# -----------------------------------------------------------------------------
# Tests: Bulk Assign
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bulk_assign_status():
    """Test bulk assign for status field."""
    data_source = MockDataSource()
    manager = BulkActionManager(data_source)

    result = await manager.bulk_assign(
        ids=[1, 3, 5],
        field_name="status",
        value="published",
        create_snapshot=False,
    )

    assert result.success
    assert result.affected_count == 3

    # Verify assignments
    records = await data_source.fetch_by_ids([1, 3, 5])
    assert all(r["status"] == "published" for r in records)


@pytest.mark.asyncio
async def test_bulk_assign_owner():
    """Test bulk assign for owner field."""
    data_source = MockDataSource()
    manager = BulkActionManager(data_source)

    result = await manager.bulk_assign(
        ids=[1, 2, 3],
        field_name="owner_id",
        value=99,
        create_snapshot=True,
    )

    assert result.success
    assert result.affected_count == 3
    assert result.snapshot_id is not None

    # Verify assignments
    records = await data_source.fetch_by_ids([1, 2, 3])
    assert all(r["owner_id"] == 99 for r in records)


# -----------------------------------------------------------------------------
# Tests: Custom Actions
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_custom_action():
    """Test registering a custom bulk action."""
    data_source = MockDataSource()
    manager = BulkActionManager(data_source)

    # Define custom action
    async def archive_action(ids: List[Any]) -> BulkActionResult:
        return await manager.bulk_assign(ids, "status", "archived")

    # Register action
    manager.register_action("archive", archive_action)

    # Execute action
    result = await manager.execute_action("archive", [1, 2])

    assert result.success
    assert result.affected_count == 2

    # Verify
    records = await data_source.fetch_by_ids([1, 2])
    assert all(r["status"] == "archived" for r in records)


@pytest.mark.asyncio
async def test_execute_unknown_action():
    """Test executing an unknown action returns error."""
    data_source = MockDataSource()
    manager = BulkActionManager(data_source)

    result = await manager.execute_action("nonexistent", [1, 2])

    assert not result.success
    assert "Unknown action" in result.errors[0]


@pytest.mark.asyncio
async def test_bulk_action_decorator():
    """Test @bulk_action decorator stores metadata."""

    @bulk_action("publish", "Publish Selected", icon="check", danger=False)
    async def publish_posts(manager, ids):
        return await manager.bulk_assign(ids, "status", "published")

    # Check metadata
    assert hasattr(publish_posts, "_bulk_action_meta")
    meta = publish_posts._bulk_action_meta
    assert meta["name"] == "publish"
    assert meta["label"] == "Publish Selected"
    assert meta["icon"] == "check"
    assert meta["confirm"] is True
    assert meta["danger"] is False


# -----------------------------------------------------------------------------
# Tests: Preview
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_preview():
    """Test getting preview of affected records."""
    data_source = MockDataSource()
    manager = BulkActionManager(data_source)

    preview = await manager.get_preview([1, 2, 3, 4, 5], limit=3)

    assert len(preview) == 3
    assert preview[0]["id"] == 1
    assert preview[1]["id"] == 2
    assert preview[2]["id"] == 3


@pytest.mark.asyncio
async def test_get_confirmation_message():
    """Test generating confirmation message."""
    data_source = MockDataSource()
    manager = BulkActionManager(data_source)

    # Without preview
    msg = manager.get_confirmation_message("delete", 5)
    assert "delete 5 record(s)" in msg

    # With preview
    preview = await manager.get_preview([1, 2])
    msg = manager.get_confirmation_message("archive", 2, preview)
    assert "archive 2 record(s)" in msg
    assert "This will affect:" in msg


# -----------------------------------------------------------------------------
# Tests: Progress Tracking
# -----------------------------------------------------------------------------


