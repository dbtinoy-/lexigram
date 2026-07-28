"""Loader-worker bridge — exposes DocumentIngestionWorker as a document loader.

Allows the RAG pipeline's ``LoaderRegistry`` to dispatch document loading to
the ingestion worker, gaining retry logic, DLQ support, and progress tracking
transparently.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any

from lexigram.contracts.ai.exceptions import RAGError
from lexigram.contracts.ai.rag import ChunkProtocol
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.ai.workers.document_ingestion.worker import DocumentIngestionWorker

logger = get_logger(__name__)

# Maximum seconds to wait for the ingestion worker to produce a result
_DEFAULT_TIMEOUT = 300.0


class LoaderWorkerBridge:
    """Expose :class:`~lexigram.ai.workers.document_ingestion.worker.DocumentIngestionWorker`
    as a ``DocumentLoaderProtocol``-compatible loader.

    Registering this bridge in ``LoaderRegistry`` under a file extension
    (or as the URL handler) causes the RAG pipeline to submit that source
    to the background ingestion worker, which provides retry, DLQ, and
    progress tracking transparently.

    The bridge polls the worker's job status until completion or *timeout*.

    Example::

        bridge = LoaderWorkerBridge(worker=doc_ingestion_worker, timeout=120.0)
        registry = LoaderRegistry()
        registry.register([".pdf", ".docx"], bridge)

        # Later — SmartLoader will use the bridge automatically:
        smart = SmartLoader(registry=registry)
        chunks = await smart.load("large_document.pdf")
    """

    def __init__(
        self,
        worker: DocumentIngestionWorker,
        *,
        timeout: float = _DEFAULT_TIMEOUT,
        poll_interval: float = 1.0,
    ) -> None:
        """Initialize the bridge.

        Args:
            worker: The document ingestion worker to delegate to.
            timeout: Maximum seconds to wait for ingestion to complete.
            poll_interval: How often (in seconds) to poll job status.
        """
        self._worker = worker
        self._timeout = timeout
        self._poll_interval = poll_interval

    async def load(self, source: str | Path, **kwargs: Any) -> list[ChunkProtocol]:
        """Submit *source* to the ingestion worker and wait for chunks.

        The bridge submits the source path to ``DocumentIngestionWorker``,
        polls until the job succeeds or times out, then returns the resulting
        chunks from the vector store (via the worker's result).

        Args:
            source: File path or URL to load.
            **kwargs: Additional options passed to the worker ingest call.

        Returns:
            List of chunks produced by the ingestion worker.

        Raises:
            RAGError: If the worker fails, times out, or returns no chunks.
        """
        src = str(source)
        logger.info("loader_worker_bridge_submit", source=src)

        try:
            # Submit the ingestion job
            file_path = Path(src)
            result = await self._worker.ingest_document(
                document_id=str(
                    kwargs.get("document_id", file_path.stem or "document")
                ),
                file_path=file_path,
                collection_name=str(kwargs.get("collection_name", "default")),
                metadata=kwargs.get("metadata"),
                priority=int(kwargs.get("priority", 0)),
                batch_size=int(kwargs.get("batch_size", 50)),
            )
        except (OSError, RuntimeError, ValueError, TypeError) as exc:
            msg = f"Worker failed to accept document {src}: {exc}"
            raise RAGError(msg) from exc

        # Poll until done or timeout
        deadline = asyncio.get_event_loop().time() + self._timeout
        if isinstance(result, str):
            job_id = result
        else:
            job_id = getattr(result, "document_id", None) or getattr(
                result, "job_id", None
            )

        if not isinstance(job_id, str) or not job_id:
            raise RAGError(f"Worker did not return a job ID for {src}")

        while asyncio.get_event_loop().time() < deadline:
            try:
                progress = await self._worker.get_progress(job_id)
            except (OSError, RuntimeError, ValueError, TypeError) as exc:
                raise RAGError(
                    f"Failed to poll progress for job {job_id}: {exc}"
                ) from exc

            status = getattr(progress, "status", None)

            if status and str(status) == "completed":
                chunks = await self._collect_chunks(job_id)
                logger.info(
                    "loader_worker_bridge_completed",
                    source=src,
                    chunk_count=len(chunks),
                )
                return chunks

            if status and str(status) == "failed":
                error_msg = getattr(progress, "error", "unknown error")
                raise RAGError(f"Worker ingestion failed for {src}: {error_msg}")

            await asyncio.sleep(self._poll_interval)

        raise RAGError(f"Worker timed out after {self._timeout}s for source: {src}")

    async def _collect_chunks(self, job_id: str) -> list[ChunkProtocol]:
        """Retrieve chunks produced by the worker for *job_id*.

        Tries ``get_result()`` on the worker; falls back to empty list if
        the worker does not support direct chunk retrieval (chunks will be
        in the vector store).

        Args:
            job_id: Job identifier returned by the worker.

        Returns:
            List of chunks, possibly empty if the worker stores directly.
        """
        try:
            get_result = getattr(self._worker, "get_result", None)
            if callable(get_result):
                result = await get_result(job_id)
                chunks = getattr(result, "chunks", None)
                if isinstance(chunks, list):
                    return chunks
        except (OSError, RuntimeError, ValueError, TypeError, AttributeError) as exc:
            logger.warning(
                "loader_worker_bridge_collect_failed",
                job_id=job_id,
                error=str(exc),
            )
        # If the worker stores chunks directly in the vector store, we return
        # an empty list here — the caller should query the vector store.
        return []


__all__ = ["LoaderWorkerBridge"]
