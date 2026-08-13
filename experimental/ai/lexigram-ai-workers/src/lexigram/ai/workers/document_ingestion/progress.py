"""
Progress tracking for document ingestion.

Handles progress updates and tracking across ingestion jobs.
"""

from __future__ import annotations

import asyncio
from typing import Any

from lexigram.ai.workers.document_ingestion.types import (
    IngestionProgress,
    IngestionStatus,
)


class ProgressTracker:
    """Tracks progress of document ingestion jobs."""

    def __init__(self) -> None:
        """Initialize progress tracker."""
        self._progress: dict[str, IngestionProgress] = {}
        self._progress_lock = asyncio.Lock()

    async def initialize_progress(self, job_id: str, document_id: str) -> None:
        """Initialize progress tracking for a job."""
        async with self._progress_lock:
            self._progress[job_id] = IngestionProgress(
                document_id=document_id,
                status=IngestionStatus.PENDING,
            )

    async def get_progress(self, job_id: str) -> IngestionProgress | None:
        """Get ingestion progress for job."""
        async with self._progress_lock:
            return self._progress.get(job_id)

    async def update_progress(
        self,
        document_id: str,
        status: IngestionStatus | None = None,
        total_chunks: int | None = None,
        chunks_processed: int | None = None,
        error: str | None = None,
    ) -> None:
        """Update ingestion progress."""
        async with self._progress_lock:
            # Find progress by document_id
            for progress in self._progress.values():
                if progress.document_id == document_id:
                    if total_chunks is not None:
                        progress.total_chunks = total_chunks
                    progress.update(
                        status=status,
                        chunks_processed=chunks_processed,
                        error=error,
                    )
                    break

    async def get_all_progress(self) -> dict[str, IngestionProgress]:
        """Get all progress entries."""
        async with self._progress_lock:
            return self._progress.copy()

    def get_stats(self) -> dict[str, Any]:
        """Get progress tracking statistics."""
        return {
            "active_jobs": len(self._progress),
            "completed_jobs": sum(
                1
                for p in self._progress.values()
                if p.status == IngestionStatus.COMPLETED
            ),
            "failed_jobs": sum(
                1 for p in self._progress.values() if p.status == IngestionStatus.FAILED
            ),
        }
