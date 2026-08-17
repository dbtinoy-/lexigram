"""Unit tests for workers provider and RAG bridge adapters."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.workers.adapters.loader_worker import LoaderWorkerBridge
from lexigram.ai.workers.adapters.rag_adapter import IngestionError, RAGIngestionAdapter
from lexigram.ai.workers.config import WorkersConfig
from lexigram.ai.workers.di.provider import WorkersProvider
from lexigram.ai.workers.document_ingestion.types import Document
from lexigram.ai.workers.exceptions import WorkerError
from lexigram.contracts.ai.exceptions import RAGError
from lexigram.contracts.ai.rag import ChunkProtocol


@dataclass(slots=True)
class _TestChunk:
    text: str
    metadata: dict[str, Any]
    score: float | None = None


def _chunk(text: str, idx: int = 0) -> ChunkProtocol:
    return _TestChunk(
        text=text,
        metadata={"kind": "unit", "source": "test-source", "chunk_index": idx},
    )


# ---------------------------------------------------------------------------
# WorkersProvider
# ---------------------------------------------------------------------------


class TestWorkersProvider:
    @pytest.fixture
    def mock_registrar(self) -> MagicMock:
        container = MagicMock()
        container.singleton = MagicMock()
        container.register = MagicMock()
        return container

    @pytest.fixture
    def mock_resolver(self) -> MagicMock:
        resolver = MagicMock()
        resolver.resolve = AsyncMock()
        return resolver

    @pytest.mark.asyncio
    async def test_register_enabled_registers_all_worker_types(
        self,
        mock_registrar: MagicMock,
    ) -> None:
        provider = WorkersProvider(config=WorkersConfig(enabled=True))
        await provider.register(mock_registrar)

        # Config singleton plus four worker registrations
        mock_registrar.singleton.assert_called_once()
        assert mock_registrar.register.call_count == 4

    @pytest.mark.asyncio
    async def test_register_disabled_skips_worker_registrations(
        self,
        mock_registrar: MagicMock,
    ) -> None:
        provider = WorkersProvider(config=WorkersConfig(enabled=False))
        await provider.register(mock_registrar)

        mock_registrar.singleton.assert_called_once()
        mock_registrar.register.assert_not_called()

    @pytest.mark.asyncio
    async def test_boot_disabled_does_not_resolve_workers(
        self,
        mock_resolver: MagicMock,
    ) -> None:
        provider = WorkersProvider(config=WorkersConfig(enabled=False))
        await provider.boot(mock_resolver)
        mock_resolver.resolve.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_boot_starts_all_resolved_workers(
        self,
        mock_resolver: MagicMock,
    ) -> None:
        workers = [
            SimpleNamespace(start=AsyncMock(), stop=AsyncMock()),
            SimpleNamespace(start=AsyncMock(), stop=AsyncMock()),
            SimpleNamespace(start=AsyncMock(), stop=AsyncMock()),
            SimpleNamespace(start=AsyncMock(), stop=AsyncMock()),
        ]
        mock_resolver.resolve = AsyncMock(side_effect=workers)

        provider = WorkersProvider(config=WorkersConfig(enabled=True))
        await provider.boot(mock_resolver)

        # Let scheduled worker.start() tasks execute
        await asyncio.sleep(0)

        for worker in workers:
            worker.start.assert_awaited_once()

        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_boot_continues_when_one_worker_fails_to_resolve(
        self,
        mock_resolver: MagicMock,
    ) -> None:
        good_worker_1 = SimpleNamespace(start=AsyncMock(), stop=AsyncMock())
        good_worker_2 = SimpleNamespace(start=AsyncMock(), stop=AsyncMock())
        good_worker_3 = SimpleNamespace(start=AsyncMock(), stop=AsyncMock())

        mock_resolver.resolve = AsyncMock(
            side_effect=[
                good_worker_1,
                RuntimeError("resolve failed"),
                good_worker_2,
                good_worker_3,
            ]
        )

        provider = WorkersProvider(config=WorkersConfig(enabled=True))
        await provider.boot(mock_resolver)
        await asyncio.sleep(0)

        good_worker_1.start.assert_awaited_once()
        good_worker_2.start.assert_awaited_once()
        good_worker_3.start.assert_awaited_once()

        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_calls_stop_on_started_workers(self) -> None:
        resolver = MagicMock()
        workers = [
            SimpleNamespace(start=AsyncMock(), stop=AsyncMock()),
            SimpleNamespace(start=AsyncMock(), stop=AsyncMock()),
            SimpleNamespace(start=AsyncMock(), stop=AsyncMock()),
            SimpleNamespace(start=AsyncMock(), stop=AsyncMock()),
        ]
        resolver.resolve = AsyncMock(side_effect=workers)

        provider = WorkersProvider(config=WorkersConfig(enabled=True))
        await provider.boot(resolver)
        await asyncio.sleep(0)
        await provider.shutdown()

        for worker in workers:
            worker.stop.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_worker_task_error_is_handled_by_done_callback(self) -> None:
        async def _boom() -> None:
            raise RuntimeError("task failed")

        provider = WorkersProvider(config=WorkersConfig(enabled=True))
        task = asyncio.create_task(_boom(), name="worker.test")

        # Swallow exception to avoid test warnings while still exercising callback.
        try:
            await task
        except RuntimeError:
            pass

        provider._tasks.add(task)
        provider._on_worker_done(task)
        assert task not in provider._tasks


# ---------------------------------------------------------------------------
# RAGIngestionAdapter
# ---------------------------------------------------------------------------


class TestRAGIngestionAdapter:
    @pytest.fixture
    def chunker(self) -> MagicMock:
        mock = MagicMock()
        mock.chunk = AsyncMock()
        return mock

    @pytest.fixture
    def embedding_worker(self) -> MagicMock:
        mock = MagicMock()
        mock.embed_batch = AsyncMock(return_value="job-embed-1")
        return mock

    @pytest.fixture
    def vector_store(self) -> MagicMock:
        return MagicMock()

    @pytest.mark.asyncio
    async def test_ingest_empty_documents_returns_ok(
        self,
        chunker: MagicMock,
        embedding_worker: MagicMock,
        vector_store: MagicMock,
    ) -> None:
        adapter = RAGIngestionAdapter(chunker, embedding_worker, vector_store)
        result = await adapter.ingest_to_rag([], collection="docs")

        assert result.is_ok()
        report = result.unwrap()
        assert report.document_count == 0
        assert report.chunk_count == 0
        embedding_worker.embed_batch.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_ingest_successful_path_submits_all_chunks(
        self,
        chunker: MagicMock,
        embedding_worker: MagicMock,
        vector_store: MagicMock,
    ) -> None:
        docs = [
            Document(content="doc1", metadata={"document_id": "d1"}),
            Document(content="doc2", metadata={"document_id": "d2"}),
        ]
        chunker.chunk = AsyncMock(
            side_effect=[
                [_chunk("d1-a", 0), _chunk("d1-b", 1)],
                [_chunk("d2-a", 0)],
            ]
        )

        adapter = RAGIngestionAdapter(chunker, embedding_worker, vector_store)
        result = await adapter.ingest_to_rag(
            docs,
            collection="docs",
            model_name="embed-model",
            batch_size=50,
        )

        assert result.is_ok()
        report = result.unwrap()
        assert report.document_count == 2
        assert report.chunk_count == 3
        assert report.embedding_job_id == "job-embed-1"

        embedding_worker.embed_batch.assert_awaited_once()
        kwargs = embedding_worker.embed_batch.await_args.kwargs
        assert kwargs["collection_name"] == "docs"
        assert kwargs["model_name"] == "embed-model"
        assert kwargs["batch_size"] == 50
        assert len(kwargs["chunks"]) == 3

    @pytest.mark.asyncio
    async def test_ingest_partial_chunk_failures_still_succeeds(
        self,
        chunker: MagicMock,
        embedding_worker: MagicMock,
        vector_store: MagicMock,
    ) -> None:
        docs = [
            Document(content="bad", metadata={"document_id": "bad-1"}),
            Document(content="good", metadata={"document_id": "good-1"}),
        ]
        chunker.chunk = AsyncMock(
            side_effect=[
                ValueError("cannot chunk"),
                [_chunk("ok", 0)],
            ]
        )

        adapter = RAGIngestionAdapter(chunker, embedding_worker, vector_store)
        result = await adapter.ingest_to_rag(docs, collection="docs")

        assert result.is_ok()
        report = result.unwrap()
        assert report.document_count == 2
        assert report.chunk_count == 1

    @pytest.mark.asyncio
    async def test_ingest_all_chunk_failures_returns_err(
        self,
        chunker: MagicMock,
        embedding_worker: MagicMock,
        vector_store: MagicMock,
    ) -> None:
        docs = [
            Document(content="bad", metadata={"document_id": "d1"}),
            Document(content="bad2", metadata={"document_id": "d2"}),
        ]
        chunker.chunk = AsyncMock(
            side_effect=[RuntimeError("bad1"), RuntimeError("bad2")]
        )

        adapter = RAGIngestionAdapter(chunker, embedding_worker, vector_store)
        result = await adapter.ingest_to_rag(docs)

        assert result.is_err()
        error = result.unwrap_err()
        assert isinstance(error, IngestionError)
        assert error.document_ids == ["d1", "d2"]
        embedding_worker.embed_batch.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_ingest_chunk_failure_uses_unknown_id_when_missing(
        self,
        chunker: MagicMock,
        embedding_worker: MagicMock,
        vector_store: MagicMock,
    ) -> None:
        docs = [Document(content="bad", metadata={})]
        chunker.chunk = AsyncMock(side_effect=[RuntimeError("boom")])

        adapter = RAGIngestionAdapter(chunker, embedding_worker, vector_store)
        result = await adapter.ingest_to_rag(docs)

        assert result.is_err()
        assert result.unwrap_err().document_ids == ["unknown"]

    @pytest.mark.asyncio
    async def test_ingest_embed_failure_raises_worker_error(
        self,
        chunker: MagicMock,
        embedding_worker: MagicMock,
        vector_store: MagicMock,
    ) -> None:
        chunker.chunk = AsyncMock(return_value=[_chunk("c1")])
        embedding_worker.embed_batch = AsyncMock(side_effect=RuntimeError("embed down"))

        adapter = RAGIngestionAdapter(chunker, embedding_worker, vector_store)

        with pytest.raises(WorkerError):
            await adapter.ingest_to_rag([Document(content="doc", metadata={})])


# ---------------------------------------------------------------------------
# LoaderWorkerBridge
# ---------------------------------------------------------------------------


class TestLoaderWorkerBridge:
    @staticmethod
    def _source_path(tmp_path: Path) -> str:
        return str(tmp_path / "test.txt")

    @pytest.mark.asyncio
    async def test_load_success_returns_worker_chunks(self, tmp_path: Path) -> None:
        worker = MagicMock()
        worker.ingest_document = AsyncMock(return_value=SimpleNamespace(job_id="job-1"))
        worker.get_progress = AsyncMock(
            side_effect=[
                SimpleNamespace(status="pending"),
                SimpleNamespace(status="completed"),
            ]
        )
        chunks = [_chunk("a", 0), _chunk("b", 1)]
        worker.get_result = AsyncMock(return_value=SimpleNamespace(chunks=chunks))

        bridge = LoaderWorkerBridge(worker=worker, timeout=1.0, poll_interval=0.0)
        result = await bridge.load(self._source_path(tmp_path))

        assert result == chunks
        worker.ingest_document.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_load_accepts_document_id_as_job_id(self, tmp_path: Path) -> None:
        worker = MagicMock()
        worker.ingest_document = AsyncMock(
            return_value=SimpleNamespace(document_id="doc-job-1")
        )
        worker.get_progress = AsyncMock(
            return_value=SimpleNamespace(status="completed")
        )
        worker.get_result = AsyncMock(return_value=SimpleNamespace(chunks=[_chunk("x")]))

        bridge = LoaderWorkerBridge(worker=worker, timeout=1.0, poll_interval=0.0)
        result = await bridge.load(self._source_path(tmp_path))
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_load_raises_when_worker_rejects_document(self, tmp_path: Path) -> None:
        worker = MagicMock()
        worker.ingest_document = AsyncMock(side_effect=RuntimeError("queue down"))

        bridge = LoaderWorkerBridge(worker=worker, timeout=1.0, poll_interval=0.0)
        with pytest.raises(RAGError):
            await bridge.load(self._source_path(tmp_path))

    @pytest.mark.asyncio
    async def test_load_raises_when_no_job_id_returned(self, tmp_path: Path) -> None:
        worker = MagicMock()
        worker.ingest_document = AsyncMock(return_value=SimpleNamespace())

        bridge = LoaderWorkerBridge(worker=worker, timeout=1.0, poll_interval=0.0)
        with pytest.raises(RAGError, match="did not return a job ID"):
            await bridge.load(self._source_path(tmp_path))

    @pytest.mark.asyncio
    async def test_load_raises_on_failed_progress_status(self, tmp_path: Path) -> None:
        worker = MagicMock()
        worker.ingest_document = AsyncMock(return_value=SimpleNamespace(job_id="job-1"))
        worker.get_progress = AsyncMock(
            return_value=SimpleNamespace(status="failed", error="parser crashed")
        )

        bridge = LoaderWorkerBridge(worker=worker, timeout=1.0, poll_interval=0.0)
        with pytest.raises(RAGError, match="parser crashed"):
            await bridge.load(self._source_path(tmp_path))

    @pytest.mark.asyncio
    async def test_load_raises_on_timeout(self, tmp_path: Path) -> None:
        worker = MagicMock()
        worker.ingest_document = AsyncMock(return_value=SimpleNamespace(job_id="job-1"))
        worker.get_progress = AsyncMock(return_value=SimpleNamespace(status="pending"))

        bridge = LoaderWorkerBridge(worker=worker, timeout=0.0, poll_interval=0.0)
        with pytest.raises(RAGError, match="timed out"):
            await bridge.load(self._source_path(tmp_path))

    @pytest.mark.asyncio
    async def test_collect_chunks_returns_empty_on_missing_get_result(self) -> None:
        worker = MagicMock(spec=["ingest_document", "get_progress"])
        bridge = LoaderWorkerBridge(worker=worker, timeout=1.0, poll_interval=0.0)
        chunks = await bridge._collect_chunks("job-1")
        assert chunks == []

    @pytest.mark.asyncio
    async def test_collect_chunks_returns_empty_on_result_error(self) -> None:
        worker = MagicMock()
        worker.get_result = AsyncMock(side_effect=RuntimeError("backend error"))
        bridge = LoaderWorkerBridge(worker=worker, timeout=1.0, poll_interval=0.0)
        chunks = await bridge._collect_chunks("job-1")
        assert chunks == []
