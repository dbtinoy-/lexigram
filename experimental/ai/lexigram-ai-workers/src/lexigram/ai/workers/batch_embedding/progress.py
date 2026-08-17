"""
Progress tracking for batch embedding operations.
"""

from __future__ import annotations

import asyncio
from typing import Any

from lexigram.ai.workers.batch_embedding.types import (
    BatchEmbeddingProgress,
    EmbeddingStatus,
)


class ProgressTracker:
    """Thread-safe progress tracking for embedding jobs."""

    def __init__(self) -> None:
        """Initialize progress tracker."""
        self._progress: dict[str, BatchEmbeddingProgress] = {}
        self._lock = asyncio.Lock()

    async def initialize_job(
        self,
        job_id: str,
        total_texts: int,
        status: EmbeddingStatus = EmbeddingStatus.PENDING,
    ) -> None:
        """Initialize progress tracking for a job."""
        async with self._lock:
            self._progress[job_id] = BatchEmbeddingProgress(
                job_id=job_id,
                status=status,
                total_texts=total_texts,
            )

    async def update_progress(
        self,
        job_id: str,
        status: EmbeddingStatus | None = None,
        texts_processed: int | None = None,
        cache_hits: int | None = None,
        cache_misses: int | None = None,
        error: str | None = None,
    ) -> None:
        """Update progress for a job."""
        async with self._lock:
            if job_id in self._progress:
                self._progress[job_id].update(
                    status=status,
                    texts_processed=texts_processed,
                    cache_hits=cache_hits,
                    cache_misses=cache_misses,
                    error=error,
                )

    async def get_progress(self, job_id: str) -> BatchEmbeddingProgress | None:
        """Get progress for a job."""
        async with self._lock:
            return self._progress.get(job_id)

    async def remove_job(self, job_id: str) -> None:
        """Remove progress tracking for a job."""
        async with self._lock:
            self._progress.pop(job_id, None)

    def get_active_jobs(self) -> list[str]:
        """Get list of active job IDs."""
        return list(self._progress.keys())

    def get_stats(self) -> dict[str, Any]:
        """Get progress tracking statistics."""
        return {
            "active_jobs": len(self._progress),
            "jobs_by_status": {
                status.value: sum(
                    1 for p in self._progress.values() if p.status == status
                )
                for status in EmbeddingStatus
            },
        }
