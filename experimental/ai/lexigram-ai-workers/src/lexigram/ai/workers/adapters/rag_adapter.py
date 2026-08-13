"""RAG ingestion adapter — bridges DocumentIngestionWorker to the RAG pipeline.

Takes parsed documents from the ingestion worker, runs them through the RAG
chunking pipeline, and stores embeddings via ``BatchEmbeddingWorker`` + the
vector store.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from inspect import isawaitable
from typing import TYPE_CHECKING, Any

from lexigram.ai.workers.exceptions import WorkerError
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.ai.workers.batch_embedding.worker import BatchEmbeddingWorker
    from lexigram.ai.workers.document_ingestion.types import Document
    from lexigram.contracts import VectorStoreProtocol
    from lexigram.contracts.ai.rag import ChunkProtocol
    from lexigram.contracts.ai.vector import ChunkerProtocol

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------


@dataclass
class IngestionReport:
    """Summary produced after a successful :meth:`RAGIngestionAdapter.ingest_to_rag` call.

    Attributes:
        document_count: Number of input documents processed.
        chunk_count: Total number of chunks produced and stored.
        collection: Vector store collection name.
        embedding_job_id: Job ID returned by ``BatchEmbeddingWorker``.
    """

    document_count: int
    chunk_count: int
    collection: str
    embedding_job_id: str | None = None


@dataclass
class IngestionError:
    """Domain error returned when RAG ingestion fails.

    Attributes:
        reason: Human-readable failure description.
        document_ids: IDs of documents that failed.
    """

    reason: str
    document_ids: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# RAGIngestionAdapter
# ---------------------------------------------------------------------------


class RAGIngestionAdapter:
    """Bridge from ``DocumentIngestionWorker`` output to the RAG pipeline.

    Pulls parsed :class:`~lexigram.ai.workers.document_ingestion.types.Document`
    objects, converts them to :class:`~lexigram.ai.rag.chunking.types.Chunk`
    objects via the configured ``Chunker``, then hands the chunks to
    ``BatchEmbeddingWorker`` for embedding and vector-store persistence.

    Example::

        from lexigram.logging import get_logger

        logger = get_logger(__name__)

        adapter = RAGIngestionAdapter(
            chunker=fixed_size_chunker,
            embedding_worker=batch_worker,
            vector_store=pg_vector_store,
        )
        result = await adapter.ingest_to_rag(documents, collection="support-docs")
        if result.is_ok():
            logger.info("rag_ingestion_complete", chunk_count=result.unwrap().chunk_count)
    """

    def __init__(
        self,
        chunker: ChunkerProtocol,
        embedding_worker: BatchEmbeddingWorker,
        vector_store: VectorStoreProtocol,
    ) -> None:
        """Initialize the adapter.

        Args:
            chunker: Chunking strategy to apply to each document.
            embedding_worker: Worker that generates and stores embeddings.
            vector_store: Vector store for final chunk persistence.
        """
        self._chunker = chunker
        self._embedding_worker = embedding_worker
        self._vector_store = vector_store

    async def ingest_to_rag(
        self,
        documents: list[Document],
        *,
        collection: str = "default",
        model_name: str = "text-embedding-ada-002",
        batch_size: int = 100,
    ) -> Result[IngestionReport, IngestionError]:
        """Chunk, embed, and store a list of documents in the vector store.

        Args:
            documents: Parsed documents from the ingestion worker.
            collection: Target vector store collection name.
            model_name: Embedding model to use.
            batch_size: Number of chunks per embedding batch.

        Returns:
            ``Ok(IngestionReport)`` on success,
            ``Err(IngestionError)`` when chunking or embedding fails.
        """
        if not documents:
            return Ok(
                IngestionReport(document_count=0, chunk_count=0, collection=collection)
            )

        all_chunks: list[ChunkProtocol] = []
        failed_ids: list[str] = []

        for doc in documents:
            try:
                chunk_result: Any = self._chunker.chunk(
                    doc.content,
                    metadata=doc.metadata,
                )
                if isawaitable(chunk_result):
                    chunk_result = await chunk_result
                chunks = list(chunk_result)
                all_chunks.extend(chunks)
            except Exception as exc:  # noqa: BLE001
                doc_id = str(doc.metadata.get("document_id", "unknown"))
                logger.warning(
                    "rag_adapter_chunking_failed",
                    document_id=doc_id,
                    error=str(exc),
                )
                failed_ids.append(doc_id)

        if failed_ids and not all_chunks:
            return Err(
                IngestionError(
                    reason="All documents failed chunking",
                    document_ids=failed_ids,
                )
            )

        logger.info(
            "rag_adapter_submitting_embedding",
            chunk_count=len(all_chunks),
            collection=collection,
        )

        try:
            job_id = await self._embedding_worker.embed_batch(
                chunks=all_chunks,
                collection_name=collection,
                model_name=model_name,
                batch_size=batch_size,
            )
        except Exception as exc:
            raise WorkerError(f"Embedding worker failed: {exc}") from exc

        return Ok(
            IngestionReport(
                document_count=len(documents),
                chunk_count=len(all_chunks),
                collection=collection,
                embedding_job_id=job_id,
            )
        )


__all__ = [
    "IngestionError",
    "IngestionReport",
    "RAGIngestionAdapter",
]
