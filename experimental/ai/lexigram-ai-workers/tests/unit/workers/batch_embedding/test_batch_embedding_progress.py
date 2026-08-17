"""Tests for batch embedding progress tracking."""

from __future__ import annotations

import pytest

from lexigram.ai.workers.batch_embedding.progress import ProgressTracker
from lexigram.ai.workers.batch_embedding.types import EmbeddingStatus


class TestBatchEmbeddingProgressTracker:
    """Test ProgressTracker class for batch embedding."""

    @pytest.fixture
    def tracker(self) -> ProgressTracker:
        """Create a ProgressTracker instance."""
        return ProgressTracker()

    @pytest.mark.asyncio
    async def test_initialize_job(self, tracker: ProgressTracker) -> None:
        """Test initializing a job."""
        await tracker.initialize_job("job-1", total_texts=100)
        progress = await tracker.get_progress("job-1")
        assert progress is not None
        assert progress.job_id == "job-1"
        assert progress.total_texts == 100
        assert progress.status == EmbeddingStatus.PENDING

    @pytest.mark.asyncio
    async def test_initialize_job_with_custom_status(self, tracker: ProgressTracker) -> None:
        """Test initializing a job with custom status."""
        await tracker.initialize_job(
            "job-1",
            total_texts=100,
            status=EmbeddingStatus.PROCESSING,
        )
        progress = await tracker.get_progress("job-1")
        assert progress is not None
        assert progress.status == EmbeddingStatus.PROCESSING

    @pytest.mark.asyncio
    async def test_get_progress_nonexistent(self, tracker: ProgressTracker) -> None:
        """Test getting progress for nonexistent job returns None."""
        progress = await tracker.get_progress("nonexistent")
        assert progress is None

    @pytest.mark.asyncio
    async def test_update_progress_status(self, tracker: ProgressTracker) -> None:
        """Test updating progress status."""
        await tracker.initialize_job("job-1", total_texts=100)
        await tracker.update_progress("job-1", status=EmbeddingStatus.PROCESSING)
        progress = await tracker.get_progress("job-1")
        assert progress is not None
        assert progress.status == EmbeddingStatus.PROCESSING

    @pytest.mark.asyncio
    async def test_update_progress_texts_processed(self, tracker: ProgressTracker) -> None:
        """Test updating texts_processed."""
        await tracker.initialize_job("job-1", total_texts=100)
        await tracker.update_progress("job-1", texts_processed=50)
        progress = await tracker.get_progress("job-1")
        assert progress is not None
        assert progress.texts_processed == 50

    @pytest.mark.asyncio
    async def test_update_progress_cache_hits(self, tracker: ProgressTracker) -> None:
        """Test updating cache_hits."""
        await tracker.initialize_job("job-1", total_texts=100)
        await tracker.update_progress("job-1", cache_hits=10)
        progress = await tracker.get_progress("job-1")
        assert progress is not None
        assert progress.cache_hits == 10

    @pytest.mark.asyncio
    async def test_update_progress_cache_misses(self, tracker: ProgressTracker) -> None:
        """Test updating cache_misses."""
        await tracker.initialize_job("job-1", total_texts=100)
        await tracker.update_progress("job-1", cache_misses=5)
        progress = await tracker.get_progress("job-1")
        assert progress is not None
        assert progress.cache_misses == 5

    @pytest.mark.asyncio
    async def test_update_progress_error(self, tracker: ProgressTracker) -> None:
        """Test updating with error."""
        await tracker.initialize_job("job-1", total_texts=100)
        await tracker.update_progress("job-1", error="API failed")
        progress = await tracker.get_progress("job-1")
        assert progress is not None
        assert progress.error == "API failed"
        assert progress.status == EmbeddingStatus.FAILED

    @pytest.mark.asyncio
    async def test_update_progress_nonexistent_job(self, tracker: ProgressTracker) -> None:
        """Test updating nonexistent job does not raise."""
        await tracker.update_progress("nonexistent", status=EmbeddingStatus.PROCESSING)
        progress = await tracker.get_progress("nonexistent")
        assert progress is None

    @pytest.mark.asyncio
    async def test_remove_job(self, tracker: ProgressTracker) -> None:
        """Test removing a job."""
        await tracker.initialize_job("job-1", total_texts=100)
        await tracker.remove_job("job-1")
        progress = await tracker.get_progress("job-1")
        assert progress is None

    @pytest.mark.asyncio
    async def test_remove_nonexistent_job(self, tracker: ProgressTracker) -> None:
        """Test removing nonexistent job does not raise."""
        await tracker.remove_job("nonexistent")

    def test_get_active_jobs_empty(self, tracker: ProgressTracker) -> None:
        """Test get_active_jobs returns empty list initially."""
        assert tracker.get_active_jobs() == []

    @pytest.mark.asyncio
    async def test_get_active_jobs(self, tracker: ProgressTracker) -> None:
        """Test get_active_jobs returns job IDs."""
        await tracker.initialize_job("job-1", total_texts=100)
        await tracker.initialize_job("job-2", total_texts=50)
        active = tracker.get_active_jobs()
        assert "job-1" in active
        assert "job-2" in active

    def test_get_stats_empty(self, tracker: ProgressTracker) -> None:
        """Test get_stats with no jobs."""
        stats = tracker.get_stats()
        assert stats["active_jobs"] == 0
        assert stats["jobs_by_status"]["pending"] == 0
        assert stats["jobs_by_status"]["completed"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_jobs(self, tracker: ProgressTracker) -> None:
        """Test get_stats with various job states."""
        await tracker.initialize_job("job-1", total_texts=100, status=EmbeddingStatus.COMPLETED)
        await tracker.initialize_job("job-2", total_texts=50, status=EmbeddingStatus.FAILED)
        await tracker.initialize_job("job-3", total_texts=25, status=EmbeddingStatus.PROCESSING)

        stats = tracker.get_stats()
        assert stats["active_jobs"] == 3
        assert stats["jobs_by_status"]["completed"] == 1
        assert stats["jobs_by_status"]["failed"] == 1
        assert stats["jobs_by_status"]["processing"] == 1


class TestBatchEmbeddingProgressTrackerIsolation:
    """Test ProgressTracker isolation between instances."""

    @pytest.mark.asyncio
    async def test_instances_are_independent(self) -> None:
        """Test two tracker instances don't share state."""
        tracker1 = ProgressTracker()
        tracker2 = ProgressTracker()

        await tracker1.initialize_job("job-1", total_texts=100)
        await tracker2.initialize_job("job-2", total_texts=50)

        progress1 = await tracker1.get_progress("job-1")
        progress2 = await tracker2.get_progress("job-1")

        assert progress1 is not None
        assert progress2 is None