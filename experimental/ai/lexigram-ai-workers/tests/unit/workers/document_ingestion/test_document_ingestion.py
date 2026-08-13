"""Unit tests for document ingestion types and progress."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from lexigram.ai.workers.document_ingestion.types import (
    Document,
    DocumentIngestionJob,
    IngestionProgress,
    IngestionResult,
    IngestionStatus,
)
from lexigram.ai.workers.document_ingestion.progress import ProgressTracker

class TestDocumentIngestionTypes:
    def test_document(self) -> None:
        doc = Document(content="text", metadata={"key": "val"})
        assert doc.content == "text"
        assert doc.metadata["key"] == "val"

    def test_ingestion_progress(self) -> None:
        p = IngestionProgress(document_id="doc1", status=IngestionStatus.PENDING)
        assert p.progress_percent == 0.0

        p.update(status=IngestionStatus.CHUNKING, chunks_processed=5)
        assert p.status == IngestionStatus.CHUNKING
        assert p.chunks_processed == 5
        
        p.total_chunks = 10
        assert p.progress_percent == 50.0

        p.update(error="failed to parse")
        assert p.status == IngestionStatus.FAILED
        assert p.error == "failed to parse"

        d = p.to_dict()
        assert d["document_id"] == "doc1"

    def test_ingestion_result(self) -> None:
        res = IngestionResult.success_result("doc1", chunks_created=5, duration=1.0)
        assert res.success is True
        assert res.chunks_created == 5

        res_fail = IngestionResult.failure_result("doc1", error="err", duration=0.5)
        assert res_fail.success is False
        assert res_fail.error == "err"
        
        d = res.to_dict()
        assert d["success"] is True

    def test_document_ingestion_job(self) -> None:
        job = DocumentIngestionJob(
            document_id="doc1",
            file_path=Path("/tmp/test.txt"),
            collection_name="docs"
        )
        kwargs = job.to_job_kwargs()
        assert kwargs["document_id"] == "doc1"
        assert kwargs["file_path"] == "/tmp/test.txt"
        assert kwargs["collection_name"] == "docs"

class TestProgressTracker:
    @pytest.mark.asyncio
    async def test_progress_tracker(self) -> None:
        tracker = ProgressTracker()
        await tracker.initialize_progress("job1", "doc1")
        
        p = await tracker.get_progress("job1")
        assert p is not None
        assert p.document_id == "doc1"
        assert p.status == IngestionStatus.PENDING

        await tracker.update_progress("doc1", status=IngestionStatus.PARSING, total_chunks=10, chunks_processed=2)
        p2 = await tracker.get_progress("job1")
        assert p2 is not None
        assert p2.status == IngestionStatus.PARSING
        assert p2.total_chunks == 10
        assert p2.chunks_processed == 2

        all_p = await tracker.get_all_progress()
        assert "job1" in all_p

        stats = tracker.get_stats()
        assert stats["active_jobs"] == 1
        assert stats["completed_jobs"] == 0

        await tracker.update_progress("doc1", status=IngestionStatus.COMPLETED)
        stats2 = tracker.get_stats()
        assert stats2["completed_jobs"] == 1
