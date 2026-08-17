"""
Type definitions for batch embedding operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class EmbeddingStatus(StrEnum):
    """Embedding job status."""

    PENDING = "pending"
    PROCESSING = "processing"
    CACHING = "caching"
    STORING = "storing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BatchEmbeddingProgress:
    """Track progress of batch embedding job."""

    job_id: str
    status: EmbeddingStatus
    total_texts: int = 0
    texts_processed: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    error: str | None = None

    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage."""
        if self.total_texts == 0:
            return 0.0
        return (self.texts_processed / self.total_texts) * 100

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return (self.cache_hits / total) * 100

    def update(
        self,
        status: EmbeddingStatus | None = None,
        texts_processed: int | None = None,
        cache_hits: int | None = None,
        cache_misses: int | None = None,
        error: str | None = None,
    ) -> None:
        """Update progress tracking."""
        if status is not None:
            self.status = status
        if texts_processed is not None:
            self.texts_processed = texts_processed
        if cache_hits is not None:
            self.cache_hits += cache_hits
        if cache_misses is not None:
            self.cache_misses += cache_misses
        if error is not None:
            self.error = error
            self.status = EmbeddingStatus.FAILED
        self.updated_at = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "total_texts": self.total_texts,
            "texts_processed": self.texts_processed,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.cache_hit_rate,
            "progress_percent": self.progress_percent,
            "started_at": self.started_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "error": self.error,
        }


@dataclass
class BatchEmbeddingResult:
    """Result of batch embedding job."""

    job_id: str
    success: bool
    embeddings_generated: int = 0
    cache_hits: int = 0
    duration_seconds: float = 0.0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success_result(
        cls,
        job_id: str,
        embeddings_generated: int,
        cache_hits: int,
        duration: float,
        metadata: dict[str, Any] | None = None,
    ) -> BatchEmbeddingResult:
        """Create successful embedding result."""
        return cls(
            job_id=job_id,
            success=True,
            embeddings_generated=embeddings_generated,
            cache_hits=cache_hits,
            duration_seconds=duration,
            metadata=metadata or {},
        )

    @classmethod
    def failure_result(
        cls,
        job_id: str,
        error: str,
        duration: float,
        metadata: dict[str, Any] | None = None,
    ) -> BatchEmbeddingResult:
        """Create failed embedding result."""
        return cls(
            job_id=job_id,
            success=False,
            error=error,
            duration_seconds=duration,
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "job_id": self.job_id,
            "success": self.success,
            "embeddings_generated": self.embeddings_generated,
            "cache_hits": self.cache_hits,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class BatchEmbeddingJob:
    """JobProtocol configuration for batch embedding."""

    chunks: list[Chunk]  # type: ignore[name-defined] # Forward reference
    collection_name: str
    model_name: str | None = None
    batch_size: int = 100  # Process 100 texts per API call
    use_cache: bool = True

    def to_job_kwargs(self) -> dict[str, Any]:
        """Convert to JobProtocol kwargs."""
        model_name = self.model_name
        if model_name is None:
            model_name = "text-embedding-ada-002"

        return {
            "chunks": [{"text": c.text, "metadata": c.metadata} for c in self.chunks],
            "collection_name": self.collection_name,
            "model_name": model_name,
            "batch_size": self.batch_size,
            "use_cache": self.use_cache,
        }
