"""Unit tests for lexigram.ai.workers.document_ingestion.worker."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from lexigram.result import Ok

from lexigram.ai.workers.document_ingestion.types import (
    IngestionProgress,
    IngestionResult,
    IngestionStatus,
)
from lexigram.ai.workers.document_ingestion.worker import DocumentIngestionWorker


class TestDocumentIngestionWorker:
    @pytest.fixture
    def queue(self) -> MagicMock:
        q = MagicMock()
        q.enqueue = AsyncMock(return_value=Ok("job-doc1"))
        return q

    @pytest.fixture
    def store(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def worker(self, store, queue) -> DocumentIngestionWorker:
        return DocumentIngestionWorker(
            vector_store=store,
            queue=queue,
            concurrency=1,
        )

    @pytest.mark.asyncio
    async def test_ingest_document(self, worker: DocumentIngestionWorker, queue: MagicMock) -> None:
        job_id = await worker.ingest_document(
            document_id="doc1",
            file_path=Path("/tmp/foo.txt"),
            collection_name="docs"
        )
        queue.enqueue.assert_awaited_once()
        assert job_id == "job-doc1"
        
        prog = await worker.get_progress("job-doc1")
        assert prog.document_id == "doc1"
        assert prog.status == IngestionStatus.PENDING

    @pytest.mark.asyncio
    @patch("lexigram.di.resolution.context.get_resolver")
    async def test_start_stop(self, mock_get_resolver, worker: DocumentIngestionWorker) -> None:
        mock_worker_instance = MagicMock()
        mock_worker_instance.start = AsyncMock()
        mock_worker_instance.stop = AsyncMock()
        mock_class = MagicMock(return_value=mock_worker_instance)
        
        mock_resolver = AsyncMock()
        mock_resolver.resolve = AsyncMock(return_value=mock_class)
        mock_get_resolver.return_value = mock_resolver
        
        await worker.start()
        assert worker._running is True
        assert len(worker._workers) == 1
        mock_worker_instance.start.assert_awaited_once()

        await worker.stop()
        assert worker._running is False
        assert len(worker._workers) == 0

    @pytest.mark.asyncio
    async def test_handle_ingest_document(self, worker: DocumentIngestionWorker) -> None:
        # Mock the processor
        worker.processor.process_document = AsyncMock(
            return_value=IngestionResult.success_result("doc1", chunks_created=10, duration=2.0)
        )
        
        res = await worker._handle_ingest_document(
            document_id="doc1",
            file_path="/tmp/test.txt",
            collection_name="docs",
            parser_name=None,
            metadata={},
        )
        
        assert res.success is True
        assert res.chunks_created == 10
        worker.processor.process_document.assert_awaited_once()

    def test_get_stats(self, worker: DocumentIngestionWorker) -> None:
        stats = worker.get_stats()
        assert stats["worker_id"] == "document-ingestion"
        assert stats["running"] is False
        assert stats["concurrency"] == 1
