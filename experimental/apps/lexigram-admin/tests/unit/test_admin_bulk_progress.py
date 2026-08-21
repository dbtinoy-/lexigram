"""
BulkActionManager progress tracking: progress snapshots, error surfaces,
serialization, and execute-with-progress reporting.
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
async def test_bulk_action_progress():
    """Test BulkActionProgress tracking."""
    progress = BulkActionProgress(total=10)

    assert progress.total == 10
    assert progress.current == 0
    assert progress.percentage == 0.0

    progress.increment(3)
    assert progress.current == 3
    assert progress.percentage == 30.0

    progress.increment(7)
    assert progress.current == 10
    assert progress.percentage == 100.0


@pytest.mark.asyncio
async def test_progress_errors():
    """Test progress error tracking."""
    progress = BulkActionProgress(total=5)

    progress.add_error("Error 1")
    progress.add_error("Error 2")

    assert len(progress.errors) == 2
    assert "Error 1" in progress.errors
    assert "Error 2" in progress.errors


@pytest.mark.asyncio
async def test_progress_to_dict():
    """Test converting progress to dictionary."""
    progress = BulkActionProgress(total=10)
    progress.increment(5)
    progress.add_error("Test error")

    data = progress.to_dict()

    assert data["total"] == 10
    assert data["current"] == 5
    assert data["percentage"] == 50.0
    assert "elapsed_ms" in data
    assert len(data["errors"]) == 1


@pytest.mark.asyncio
async def test_execute_with_progress():
    """Test executing bulk action with progress tracking."""
    data_source = MockDataSource()
    cache = SimpleCache()
    manager = BulkActionManager(data_source, cache)

    # Handler that processes one record
    async def process_record(record_id, progress):
        # Simulate some work
        await asyncio.sleep(0.01)
        await data_source.bulk_update([record_id], {"status": "processed"})

    result = await manager.execute_with_progress(
        ids=[1, 2, 3],
        handler=process_record,
        batch_size=1,
    )

    assert result.success
    assert result.affected_count == 3
    assert "progress_key" in result.metadata

    # Check progress was cached
    progress_key = result.metadata["progress_key"]
    progress_data = await manager.get_progress(progress_key)
    assert progress_data is not None
    assert progress_data["current"] == 3


@pytest.mark.asyncio
async def test_execute_with_progress_errors():
    """Test progress tracking with errors."""
    data_source = MockDataSource()
    manager = BulkActionManager(data_source)

    # Handler that fails for some records
    async def process_record(record_id, progress):
        if record_id == 2:
            raise ValueError(f"Failed to process {record_id}")
        await data_source.bulk_update([record_id], {"status": "processed"})

    result = await manager.execute_with_progress(
        ids=[1, 2, 3],
        handler=process_record,
    )

    # Should attempt all records, but only 2 succeed (record 2 fails)
    assert result.affected_count == 2  # Only records 1 and 3 processed
    assert len(result.errors) == 1
    assert "Failed to process 2" in result.errors[0]


# -----------------------------------------------------------------------------
# Tests: Undo Functionality
# -----------------------------------------------------------------------------


