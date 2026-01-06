"""Tests for batch embedding types."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from lexigram.ai.workers.batch_embedding.types import (
    BatchEmbeddingJob,
    BatchEmbeddingProgress,
    BatchEmbeddingResult,
    EmbeddingStatus,
)


class TestEmbeddingStatus:
    """Test EmbeddingStatus enum."""

    def test_values(self) -> None:
        """Test all embedding status values."""
        assert EmbeddingStatus.PENDING.value == "pending"
        assert EmbeddingStatus.PROCESSING.value == "processing"
        assert EmbeddingStatus.CACHING.value == "caching"
        assert EmbeddingStatus.STORING.value == "storing"
        assert EmbeddingStatus.COMPLETED.value == "completed"
        assert EmbeddingStatus.FAILED.value == "failed"

    def test_is_str_enum(self) -> None:
        """Test it's a StrEnum."""
        assert isinstance(EmbeddingStatus.PENDING, str)


class TestBatchEmbeddingProgress:
    """Test BatchEmbeddingProgress dataclass."""

    def test_creation(self) -> None:
        """Test creating BatchEmbeddingProgress."""
        progress = BatchEmbeddingProgress(
            job_id="job-1",
            status=EmbeddingStatus.PENDING,
            total_texts=100,
        )
        assert progress.job_id == "job-1"
        assert progress.status == EmbeddingStatus.PENDING
        assert progress.total_texts == 100

    def test_default_values(self) -> None:
        """Test default values."""
        progress = BatchEmbeddingProgress(
            job_id="job-1",
            status=EmbeddingStatus.PENDING,
        )
        assert progress.total_texts == 0
        assert progress.texts_processed == 0
        assert progress.cache_hits == 0
        assert progress.cache_misses == 0
        assert progress.error is None

    def test_progress_percent_zero_texts(self) -> None:
        """Test progress_percent returns 0 when total_texts is 0."""
        progress = BatchEmbeddingProgress(
            job_id="job-1",
            status=EmbeddingStatus.PENDING,
            total_texts=0,
        )
        assert progress.progress_percent == 0.0

    def test_progress_percent_partial(self) -> None:
        """Test progress_percent calculates correctly."""
        progress = BatchEmbeddingProgress(
            job_id="job-1",
            status=EmbeddingStatus.PROCESSING,
            total_texts=100,
            texts_processed=25,
        )
        assert progress.progress_percent == 25.0

    def test_cache_hit_rate_zero(self) -> None:
        """Test cache_hit_rate returns 0 when no cache data."""
        progress = BatchEmbeddingProgress(
            job_id="job-1",
            status=EmbeddingStatus.PENDING,
        )
        assert progress.cache_hit_rate == 0.0

    def test_cache_hit_rate_partial(self) -> None:
        """Test cache_hit_rate calculates correctly."""
        progress = BatchEmbeddingProgress(
            job_id="job-1",
            status=EmbeddingStatus.COMPLETED,
            cache_hits=75,
            cache_misses=25,
        )
        assert progress.cache_hit_rate == 75.0

    def test_cache_hit_rate_full(self) -> None:
        """Test cache_hit_rate returns 100 when all hits."""
        progress = BatchEmbeddingProgress(
            job_id="job-1",
            status=EmbeddingStatus.COMPLETED,
            cache_hits=100,
            cache_misses=0,
        )
        assert progress.cache_hit_rate == 100.0

    def test_update_status(self) -> None:
        """Test update sets status."""
        progress = BatchEmbeddingProgress(
            job_id="job-1",
            status=EmbeddingStatus.PENDING,
        )
        progress.update(status=EmbeddingStatus.PROCESSING)
        assert progress.status == EmbeddingStatus.PROCESSING

    def test_update_texts_processed(self) -> None:
        """Test update sets texts_processed."""
        progress = BatchEmbeddingProgress(
            job_id="job-1",
            status=EmbeddingStatus.PROCESSING,
        )
        progress.update(texts_processed=50)
        assert progress.texts_processed == 50

    def test_update_cache_hits_increments(self) -> None:
        """Test update increments cache_hits."""
        progress = BatchEmbeddingProgress(
            job_id="job-1",
            status=EmbeddingStatus.CACHING,
            cache_hits=5,
        )
        progress.update(cache_hits=10)
        assert progress.cache_hits == 15

    def test_update_cache_misses_increments(self) -> None:
        """Test update increments cache_misses."""
        progress = BatchEmbeddingProgress(
            job_id="job-1",
            status=EmbeddingStatus.CACHING,
            cache_misses=3,
        )
        progress.update(cache_misses=7)
        assert progress.cache_misses == 10

    def test_update_error_sets_failed_status(self) -> None:
        """Test update with error sets status to FAILED."""
        progress = BatchEmbeddingProgress(
            job_id="job-1",
            status=EmbeddingStatus.PROCESSING,
        )
        progress.update(error="Model unavailable")
        assert progress.error == "Model unavailable"
        assert progress.status == EmbeddingStatus.FAILED

    def test_to_dict(self) -> None:
        """Test to_dict serialization."""
        now = datetime.now(UTC)
        progress = BatchEmbeddingProgress(
            job_id="job-1",
            status=EmbeddingStatus.COMPLETED,
            total_texts=100,
            texts_processed=100,
            cache_hits=80,
            cache_misses=20,
            started_at=now,
            updated_at=now,
        )
        d = progress.to_dict()
        assert d["job_id"] == "job-1"
        assert d["status"] == "completed"
        assert d["total_texts"] == 100
        assert d["texts_processed"] == 100
        assert d["cache_hit_rate"] == 80.0


class TestBatchEmbeddingResult:
    """Test BatchEmbeddingResult dataclass."""

    def test_creation(self) -> None:
        """Test creating BatchEmbeddingResult."""
        result = BatchEmbeddingResult(
            job_id="job-1",
            success=True,
            embeddings_generated=100,
            cache_hits=50,
            duration_seconds=5.5,
        )
        assert result.job_id == "job-1"
        assert result.success is True
        assert result.embeddings_generated == 100

    def test_success_result_factory(self) -> None:
        """Test success_result factory method."""
        result = BatchEmbeddingResult.success_result(
            job_id="job-1",
            embeddings_generated=100,
            cache_hits=50,
            duration=5.5,
        )
        assert result.success is True
        assert result.embeddings_generated == 100
        assert result.cache_hits == 50
        assert result.error is None

    def test_success_result_with_metadata(self) -> None:
        """Test success_result with custom metadata."""
        result = BatchEmbeddingResult.success_result(
            job_id="job-1",
            embeddings_generated=100,
            cache_hits=50,
            duration=5.5,
            metadata={"model": "ada-002"},
        )
        assert result.metadata == {"model": "ada-002"}

    def test_failure_result_factory(self) -> None:
        """Test failure_result factory method."""
        result = BatchEmbeddingResult.failure_result(
            job_id="job-1",
            error="API error",
            duration=2.0,
        )
        assert result.success is False
        assert result.error == "API error"
        assert result.duration_seconds == 2.0

    def test_failure_result_with_metadata(self) -> None:
        """Test failure_result with custom metadata."""
        result = BatchEmbeddingResult.failure_result(
            job_id="job-1",
            error="API error",
            duration=2.0,
            metadata={"retry": True},
        )
        assert result.metadata == {"retry": True}

    def test_to_dict_success(self) -> None:
        """Test to_dict for successful result."""
        result = BatchEmbeddingResult(
            job_id="job-1",
            success=True,
            embeddings_generated=100,
            cache_hits=50,
            duration_seconds=5.5,
        )
        d = result.to_dict()
        assert d["job_id"] == "job-1"
        assert d["success"] is True
        assert d["embeddings_generated"] == 100

    def test_to_dict_failure(self) -> None:
        """Test to_dict for failed result."""
        result = BatchEmbeddingResult(
            job_id="job-1",
            success=False,
            error="API error",
            duration_seconds=2.0,
        )
        d = result.to_dict()
        assert d["success"] is False
        assert d["error"] == "API error"


class TestBatchEmbeddingJob:
    """Test BatchEmbeddingJob dataclass."""

    def test_creation(self) -> None:
        """Test creating BatchEmbeddingJob."""
        from dataclasses import dataclass

        @dataclass
        class Chunk:
            text: str
            metadata: dict

        chunks = [Chunk(text="hello", metadata={})]
        job = BatchEmbeddingJob(
            chunks=chunks,
            collection_name="docs",
        )
        assert job.collection_name == "docs"

    def test_default_batch_size(self) -> None:
        """Test default batch_size is 100."""
        job = BatchEmbeddingJob(
            chunks=[],  # type: ignore[arg-type]
            collection_name="docs",
        )
        assert job.batch_size == 100

    def test_default_model_name(self) -> None:
        """Test default model_name is None (uses default)."""
        job = BatchEmbeddingJob(
            chunks=[],  # type: ignore[arg-type]
            collection_name="docs",
        )
        assert job.model_name is None

    def test_default_use_cache(self) -> None:
        """Test default use_cache is True."""
        job = BatchEmbeddingJob(
            chunks=[],  # type: ignore[arg-type]
            collection_name="docs",
        )
        assert job.use_cache is True

    def test_to_job_kwargs(self) -> None:
        """Test to_job_kwargs serialization."""
        from dataclasses import dataclass

        @dataclass
        class Chunk:
            text: str
            metadata: dict

        chunks = [
            Chunk(text="hello", metadata={"source": "test"}),
            Chunk(text="world", metadata={"source": "test2"}),
        ]
        job = BatchEmbeddingJob(
            chunks=chunks,
            collection_name="docs",
            model_name="custom-model",
            batch_size=50,
            use_cache=False,
        )
        kwargs = job.to_job_kwargs()
        assert len(kwargs["chunks"]) == 2
        assert kwargs["collection_name"] == "docs"
        assert kwargs["model_name"] == "custom-model"
        assert kwargs["batch_size"] == 50
        assert kwargs["use_cache"] is False

    def test_to_job_kwargs_uses_default_model(self) -> None:
        """Test to_job_kwargs uses default model when None."""
        job = BatchEmbeddingJob(
            chunks=[],  # type: ignore[arg-type]
            collection_name="docs",
            model_name=None,
        )
        kwargs = job.to_job_kwargs()
        assert kwargs["model_name"] == "text-embedding-ada-002"