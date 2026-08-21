"""
BulkActionManager undo and snapshots: undo flows, snapshot lifecycle,
recent-snapshot history, and the underlying dataclass units.
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
async def test_undo_bulk_action():
    """Test undoing a bulk action."""
    data_source = MockDataSource()
    manager = BulkActionManager(data_source)

    # Get original values
    original = await data_source.fetch_by_ids([1, 2, 3])
    original_status = {r["id"]: r["status"] for r in original}

    # Perform bulk edit with snapshot
    result = await manager.bulk_edit(
        ids=[1, 2, 3],
        updates={"status": "archived"},
        create_snapshot=True,
    )

    assert result.success
    snapshot_id = result.snapshot_id

    # Verify changes
    updated = await data_source.fetch_by_ids([1, 2, 3])
    assert all(r["status"] == "archived" for r in updated)

    # Undo
    undo_result = await manager.undo(snapshot_id)

    assert undo_result.success
    assert undo_result.affected_count == 3

    # Verify restored
    restored = await data_source.fetch_by_ids([1, 2, 3])
    for r in restored:
        assert r["status"] == original_status[r["id"]]


@pytest.mark.asyncio
async def test_undo_removes_snapshot():
    """Test undo removes the snapshot."""
    data_source = MockDataSource()
    manager = BulkActionManager(data_source)

    # Perform action
    result = await manager.bulk_edit(
        ids=[1, 2],
        updates={"status": "archived"},
        create_snapshot=True,
    )

    snapshot_id = result.snapshot_id

    # Verify snapshot exists
    snapshots = manager.get_recent_snapshots()
    assert len(snapshots) == 1

    # Undo
    await manager.undo(snapshot_id)

    # Verify snapshot removed
    snapshots = manager.get_recent_snapshots()
    assert len(snapshots) == 0


@pytest.mark.asyncio
async def test_undo_nonexistent_snapshot():
    """Test undoing a nonexistent snapshot returns error."""
    data_source = MockDataSource()
    manager = BulkActionManager(data_source)

    result = await manager.undo("nonexistent_snap")

    assert not result.success
    assert "Snapshot not found" in result.errors[0]


@pytest.mark.asyncio
async def test_get_recent_snapshots():
    """Test getting recent snapshots."""
    data_source = MockDataSource()
    manager = BulkActionManager(data_source)

    # Create multiple snapshots
    await manager.bulk_edit([1], {"status": "a"}, create_snapshot=True)
    await manager.bulk_edit([2], {"status": "b"}, create_snapshot=True)
    await manager.bulk_edit([3], {"status": "c"}, create_snapshot=True)

    # Get recent snapshots
    snapshots = manager.get_recent_snapshots(limit=2)

    assert len(snapshots) == 2
    # Should be newest first
    assert snapshots[0].record_ids == [3]
    assert snapshots[1].record_ids == [2]


# -----------------------------------------------------------------------------
# Tests: Data Structures
# -----------------------------------------------------------------------------


def test_bulk_edit_field():
    """Test BulkEditField configuration."""
    field = BulkEditField(
        name="status",
        label="Status",
        field_type="select",
        options=[("draft", "Draft"), ("published", "Published")],
        required=True,
        help_text="Select the new status",
    )

    assert field.name == "status"
    assert field.label == "Status"
    assert field.field_type == "select"
    assert len(field.options) == 2
    assert field.required is True
    assert field.help_text == "Select the new status"


def test_bulk_assign_config():
    """Test BulkAssignConfig configuration."""
    config = BulkAssignConfig(
        field_name="owner_id",
        label="Owner",
        options=[(1, "Alice"), (2, "Bob")],
        allow_null=True,
        confirm_message="Reassign ownership?",
    )

    assert config.field_name == "owner_id"
    assert config.label == "Owner"
    assert len(config.options) == 2
    assert config.allow_null is True
    assert config.confirm_message == "Reassign ownership?"


def test_bulk_action_result():
    """Test BulkActionResult structure."""
    result = BulkActionResult(
        success=True,
        affected_count=5,
        snapshot_id="snap_1",
        duration_ms=123.45,
        metadata={"action": "test"},
    )

    assert result.success is True
    assert result.affected_count == 5
    assert result.snapshot_id == "snap_1"
    assert result.duration_ms == 123.45
    assert result.metadata["action"] == "test"
    assert len(result.errors) == 0


def test_bulk_action_snapshot():
    """Test BulkActionSnapshot structure."""
    now = datetime.now()
    snapshot = BulkActionSnapshot(
        snapshot_id="snap_1",
        action_name="bulk_edit",
        record_ids=[1, 2, 3],
        timestamp=now,
        user_id=42,
        metadata={"field": "status"},
    )

    assert snapshot.snapshot_id == "snap_1"
    assert snapshot.action_name == "bulk_edit"
    assert snapshot.record_ids == [1, 2, 3]
    assert snapshot.timestamp == now
    assert snapshot.user_id == 42
    assert snapshot.metadata["field"] == "status"
