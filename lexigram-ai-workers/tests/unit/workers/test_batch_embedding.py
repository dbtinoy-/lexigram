"""Unit tests for lexigram.ai.workers.batch_embedding.types."""

from __future__ import annotations

from typing import Any
from datetime import UTC, datetime

import pytest

from lexigram.ai.workers.batch_embedding.types import (
    BatchEmbeddingJob,
    BatchEmbeddingProgress,
    BatchEmbeddingResult,
    EmbeddingStatus,
)


class DummyChunk:
    def __init__(self, text: str, metadata: dict[str, Any] | None = None):
        self.text = text
        self.metadata = metadata or {}


class TestBatchEmbeddingProgress:
    def test_progress_percent(self) -> None:
        p = BatchEmbeddingProgress(job_id="1", status=EmbeddingStatus.PENDING)
        assert p.progress_percent == 0.0

        p.total_texts = 100
        p.texts_processed = 45
        assert p.progress_percent == 45.0

    def test_cache_hit_rate(self) -> None:
        p = BatchEmbeddingProgress(job_id="1", status=EmbeddingStatus.PROCESSING)
        assert p.cache_hit_rate == 0.0

        p.cache_hits = 80
        p.cache_misses = 20
        assert p.cache_hit_rate == 80.0

    def test_update(self) -> None:
        p = BatchEmbeddingProgress(job_id="1", status=EmbeddingStatus.PENDING)
        p.update(
            status=EmbeddingStatus.PROCESSING,
            texts_processed=10,
            cache_hits=5,
            cache_misses=5
        )
        assert p.status == EmbeddingStatus.PROCESSING
        assert p.texts_processed == 10
        assert p.cache_hits == 5
        assert p.cache_misses == 5

    def test_update_error(self) -> None:
        p = BatchEmbeddingProgress(job_id="1", status=EmbeddingStatus.PROCESSING)
        p.update(error="Some error")
        assert p.status == EmbeddingStatus.FAILED
        assert p.error == "Some error"

    def test_to_dict(self) -> None:
        p = BatchEmbeddingProgress(job_id="1", status=EmbeddingStatus.COMPLETED)
        d = p.to_dict()
        assert d["job_id"] == "1"
        assert d["status"] == "completed"


class TestBatchEmbeddingResult:
    def test_success_result(self) -> None:
        r = BatchEmbeddingResult.success_result(
            job_id="job",
            embeddings_generated=100,
            cache_hits=20,
            duration=5.0
        )
        assert r.success is True
        assert r.embeddings_generated == 100
        assert r.cache_hits == 20
        assert r.duration_seconds == 5.0

    def test_failure_result(self) -> None:
        r = BatchEmbeddingResult.failure_result(
            job_id="job",
            error="API failed",
            duration=1.0
        )
        assert r.success is False
        assert r.error == "API failed"
        assert r.duration_seconds == 1.0

    def test_to_dict(self) -> None:
        r = BatchEmbeddingResult.failure_result("1", "err", 2.0)
        d = r.to_dict()
        assert d["job_id"] == "1"
        assert d["success"] is False


class TestBatchEmbeddingJob:
    def test_to_job_kwargs(self) -> None:
        job = BatchEmbeddingJob(
            chunks=[DummyChunk("hello", {"id": 1}), DummyChunk("world")],
            collection_name="docs",
            model_name="test-model"
        )
        kwargs = job.to_job_kwargs()
        assert kwargs["collection_name"] == "docs"
        assert kwargs["model_name"] == "test-model"
        assert kwargs["batch_size"] == 100
        assert kwargs["use_cache"] is True
        
        chunks = kwargs["chunks"]
        assert len(chunks) == 2
        assert chunks[0]["text"] == "hello"
        assert chunks[0]["metadata"]["id"] == 1

    def test_to_job_kwargs_fallback_model(self) -> None:
        job = BatchEmbeddingJob(
            chunks=[DummyChunk("hello")],
            collection_name="docs",
        )
        kwargs = job.to_job_kwargs()
        assert kwargs["model_name"] == "text-embedding-ada-002"
