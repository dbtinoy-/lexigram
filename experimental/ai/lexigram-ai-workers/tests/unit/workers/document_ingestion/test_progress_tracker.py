"""Tests for document ingestion progress tracking."""

from __future__ import annotations

import pytest

from lexigram.ai.workers.document_ingestion.progress import ProgressTracker
from lexigram.ai.workers.document_ingestion.types import IngestionStatus


class TestProgressTracker:
    """Test ProgressTracker class."""

    @pytest.fixture
    def tracker(self) -> ProgressTracker:
        """Create a ProgressTracker instance."""
        return ProgressTracker()

    @pytest.mark.asyncio
    async def test_initialize_progress(self, tracker: ProgressTracker) -> None:
        """Test initializing progress for a job."""
        await tracker.initialize_progress("job-1", "doc-1")
        progress = await tracker.get_progress("job-1")
        assert progress is not None
        assert progress.document_id == "doc-1"
        assert progress.status == IngestionStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_progress_nonexistent(self, tracker: ProgressTracker) -> None:
        """Test getting progress for nonexistent job returns None."""
        progress = await tracker.get_progress("nonexistent")
        assert progress is None

    @pytest.mark.asyncio
    async def test_update_progress_status(self, tracker: ProgressTracker) -> None:
        """Test updating progress status."""
        await tracker.initialize_progress("job-1", "doc-1")
        await tracker.update_progress("doc-1", status=IngestionStatus.PARSING)
        progress = await tracker.get_progress("job-1")
        assert progress is not None
        assert progress.status == IngestionStatus.PARSING

    @pytest.mark.asyncio
    async def test_update_progress_chunks(self, tracker: ProgressTracker) -> None:
        """Test updating chunk counts."""
        await tracker.initialize_progress("job-1", "doc-1")
        await tracker.update_progress(
            "doc-1",
            total_chunks=100,
            chunks_processed=50,
        )
        progress = await tracker.get_progress("job-1")
        assert progress is not None
        assert progress.total_chunks == 100
        assert progress.chunks_processed == 50

    @pytest.mark.asyncio
    async def test_update_progress_error(self, tracker: ProgressTracker) -> None:
        """Test updating progress with error."""
        await tracker.initialize_progress("job-1", "doc-1")
        await tracker.update_progress("doc-1", error="Something went wrong")
        progress = await tracker.get_progress("job-1")
        assert progress is not None
        assert progress.error == "Something went wrong"
        assert progress.status == IngestionStatus.FAILED

    @pytest.mark.asyncio
    async def test_update_progress_finds_by_document_id(self, tracker: ProgressTracker) -> None:
        """Test that update_progress finds progress by document_id."""
        await tracker.initialize_progress("job-1", "doc-1")
        await tracker.update_progress("doc-1", status=IngestionStatus.COMPLETED)
        progress = await tracker.get_progress("job-1")
        assert progress is not None
        assert progress.status == IngestionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_get_all_progress(self, tracker: ProgressTracker) -> None:
        """Test getting all progress entries."""
        await tracker.initialize_progress("job-1", "doc-1")
        await tracker.initialize_progress("job-2", "doc-2")
        all_progress = await tracker.get_all_progress()
        assert len(all_progress) == 2
        assert "job-1" in all_progress
        assert "job-2" in all_progress

    @pytest.mark.asyncio
    async def test_get_all_progress_returns_copy(self, tracker: ProgressTracker) -> None:
        """Test get_all_progress returns a copy."""
        await tracker.initialize_progress("job-1", "doc-1")
        all_progress = await tracker.get_all_progress()
        all_progress["job-1"] = None
        original = await tracker.get_progress("job-1")
        assert original is not None

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, tracker: ProgressTracker) -> None:
        """Test get_stats with no jobs."""
        stats = tracker.get_stats()
        assert stats["active_jobs"] == 0
        assert stats["completed_jobs"] == 0
        assert stats["failed_jobs"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_jobs(self, tracker: ProgressTracker) -> None:
        """Test get_stats with various job states."""
        await tracker.initialize_progress("job-1", "doc-1")
        await tracker.update_progress("doc-1", status=IngestionStatus.COMPLETED)
        await tracker.initialize_progress("job-2", "doc-2")
        await tracker.update_progress("doc-2", status=IngestionStatus.FAILED)
        await tracker.initialize_progress("job-3", "doc-3")

        stats = tracker.get_stats()
        assert stats["active_jobs"] == 3
        assert stats["completed_jobs"] == 1
        assert stats["failed_jobs"] == 1

    @pytest.mark.asyncio
    async def test_concurrent_updates(self, tracker: ProgressTracker) -> None:
        """Test concurrent progress updates are thread-safe."""
        import asyncio

        await tracker.initialize_progress("job-1", "doc-1")

        async def update_status():
            for _ in range(10):
                await tracker.update_progress("doc-1", status=IngestionStatus.PARSING)
                await asyncio.sleep(0)

        await asyncio.gather(update_status(), update_status())
        progress = await tracker.get_progress("job-1")
        assert progress is not None


class TestProgressTrackerIsolation:
    """Test ProgressTracker isolation between instances."""

    @pytest.mark.asyncio
    async def test_instances_are_independent(self) -> None:
        """Test two tracker instances don't share state."""
        tracker1 = ProgressTracker()
        tracker2 = ProgressTracker()

        await tracker1.initialize_progress("job-1", "doc-1")
        await tracker2.initialize_progress("job-2", "doc-2")

        progress1 = await tracker1.get_progress("job-1")
        progress2 = await tracker2.get_progress("job-1")

        assert progress1 is not None
        assert progress2 is None