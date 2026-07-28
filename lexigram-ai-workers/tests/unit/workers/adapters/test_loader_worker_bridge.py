"""Unit tests for LoaderWorkerBridge."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.workers.adapters.loader_worker import LoaderWorkerBridge
from lexigram.ai.workers.document_ingestion.types import (
    IngestionStatus,
)
from lexigram.contracts.ai.exceptions import RAGError


class TestLoaderWorkerBridge:
    """Tests for LoaderWorkerBridge class."""

    @pytest.fixture
    def mock_worker(self) -> MagicMock:
        """Create a mock DocumentIngestionWorker."""
        worker = MagicMock()
        worker.ingest_document = AsyncMock(return_value="job-123")
        worker.get_progress = AsyncMock()
        return worker

    @pytest.fixture
    def bridge(self, mock_worker: MagicMock) -> LoaderWorkerBridge:
        """Create LoaderWorkerBridge instance with mock worker."""
        return LoaderWorkerBridge(worker=mock_worker, timeout=60.0, poll_interval=0.1)

    def test_bridge_initializes_with_worker(self, mock_worker: MagicMock) -> None:
        """Test __init__ sets worker and configuration."""
        bridge = LoaderWorkerBridge(worker=mock_worker, timeout=120.0, poll_interval=0.5)

        assert bridge._worker is mock_worker
        assert bridge._timeout == 120.0
        assert bridge._poll_interval == 0.5

    @pytest.mark.asyncio
    async def test_load_documents_calls_worker(self, bridge: LoaderWorkerBridge, mock_worker: MagicMock) -> None:
        """Test load_documents() invokes worker.ingest_document."""
        mock_progress = MagicMock()
        mock_progress.status = IngestionStatus.COMPLETED
        mock_worker.get_progress.return_value = mock_progress

        result = await bridge.load(Path("/test/doc.pdf"))

        mock_worker.ingest_document.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_load_documents_timeout_handling(self, bridge: LoaderWorkerBridge, mock_worker: MagicMock) -> None:
        """Test timeout parameter works correctly."""
        mock_progress = MagicMock()
        mock_progress.status = IngestionStatus.PENDING
        mock_worker.get_progress.return_value = mock_progress

        bridge._timeout = 0.2

        with pytest.raises(RAGError, match="timed out"):
            await bridge.load(Path("/test/doc.pdf"))

    @pytest.mark.asyncio
    async def test_load_documents_error_propagation(self, bridge: LoaderWorkerBridge, mock_worker: MagicMock) -> None:
        """Test worker errors propagate correctly."""
        mock_worker.ingest_document.side_effect = RuntimeError("Worker failed")

        with pytest.raises(Exception, match="Worker failed to accept document"):
            await bridge.load(Path("/test/doc.pdf"))

    @pytest.mark.asyncio
    async def test_load_with_collection_name(self, bridge: LoaderWorkerBridge, mock_worker: MagicMock) -> None:
        """Test load passes collection_name to worker."""
        mock_progress = MagicMock()
        mock_progress.status = IngestionStatus.COMPLETED
        mock_worker.get_progress.return_value = mock_progress

        await bridge.load(Path("/test/doc.pdf"), collection_name="my_collection")

        call_kwargs = mock_worker.ingest_document.call_args.kwargs
        assert call_kwargs["collection_name"] == "my_collection"

    @pytest.mark.asyncio
    async def test_load_with_document_id(self, bridge: LoaderWorkerBridge, mock_worker: MagicMock) -> None:
        """Test load uses provided document_id."""
        mock_progress = MagicMock()
        mock_progress.status = IngestionStatus.COMPLETED
        mock_worker.get_progress.return_value = mock_progress

        await bridge.load(Path("/test/doc.pdf"), document_id="custom-doc-id")

        call_kwargs = mock_worker.ingest_document.call_args.kwargs
        assert call_kwargs["document_id"] == "custom-doc-id"

    @pytest.mark.asyncio
    async def test_load_failed_status_raises_error(self, bridge: LoaderWorkerBridge, mock_worker: MagicMock) -> None:
        """Test failed status from worker raises RAGError."""
        mock_progress = MagicMock()
        mock_progress.status = IngestionStatus.FAILED
        mock_progress.error = "Ingestion failed"
        mock_worker.get_progress.return_value = mock_progress

        with pytest.raises(RAGError, match="Ingestion failed"):
            await bridge.load(Path("/test/doc.pdf"))

    @pytest.mark.asyncio
    async def test_load_get_result_fallback(self, bridge: LoaderWorkerBridge, mock_worker: MagicMock) -> None:
        """Test _collect_chunks falls back when worker has no get_result."""
        mock_progress = MagicMock()
        mock_progress.status = IngestionStatus.COMPLETED
        mock_worker.get_progress.return_value = mock_progress
        mock_worker.get_result = None

        result = await bridge.load(Path("/test/doc.pdf"))

        assert result == []
