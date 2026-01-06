"""DocumentVectorStoreAdapter — bridges embedding + pgvector into DocumentVectorStoreProtocol."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
import uuid

from lexigram.contracts.ai.vector import Document, RAGSearchResult
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.data.vector import (
    CollectionConfig,
    DistanceMetric,
    IndexType,
    SearchQuery,
)
from lexigram.contracts.data.vector.types import VectorRecord
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result
from lexigram.vector.exceptions import VectorError, VectorSearchError, VectorUpsertError

if TYPE_CHECKING:
    from lexigram.contracts.ai.vector import DocumentProtocol, SearchResultProtocol
    from lexigram.contracts.data.vector.filters import MetadataFilter
    from lexigram.vector.backends.pgvector import PgVectorStore
    from lexigram.vector.backends.pgvector.collection import PgVectorCollection
    from lexigram.vector.embedding.client import OpenAICompatibleEmbeddingClient

logger = get_logger(__name__)


class DocumentVectorStoreAdapter:
    """Adapts PgVectorStore + EmbeddingClientProtocol into DocumentVectorStoreProtocol.

    This adapter is the bridge between the AI-layer contract
    (``DocumentVectorStoreProtocol``) and the infrastructure layer
    (``PgVectorStore`` + ``PgVectorCollection``).

    Responsibilities:
    - Call the embedding client to convert text → vector before upsert / search.
    - Map ``Document`` objects to ``VectorRecord`` objects for storage.
    - Map ``SearchResult`` rows back to ``RAGSearchResult`` for consumers.
    - Honour ``Document.embedding`` when pre-computed embeddings are provided
      (skips the embedding API call for those documents).

    Lifecycle::

        adapter = DocumentVectorStoreAdapter(
            store=pgvector_store,
            embedding_client=embedding_client,
            collection_name="pet_knowledge",
            dimension=768,
        )
        await adapter.connect()   # creates collection if absent
        ...
        await adapter.close()     # closes embedding client session

    Example::

        docs = [Document(text="dog limping after run", metadata={"species": "dog"})]
        result = await adapter.add(docs)
        if result.is_ok():
            ids = result.unwrap()

        search_result = await adapter.search_text("cruciate ligament", top_k=5)
        if search_result.is_ok():
            for hit in search_result.unwrap():
                logger.info("search_result", score=hit.score, text=hit.document.text)
    """

    def __init__(
        self,
        store: PgVectorStore,
        embedding_client: OpenAICompatibleEmbeddingClient,
        collection_name: str,
        dimension: int,
        distance_metric: DistanceMetric = DistanceMetric.COSINE,
    ) -> None:
        """Initialise the adapter.

        Args:
            store: Connected ``PgVectorStore`` (``connect()`` already called).
            embedding_client: Embedding client for text → vector conversion.
            collection_name: Name of the pgvector table / collection to use.
            dimension: Vector dimension — must match the embedding model output.
            distance_metric: Similarity metric for search (default: cosine).
        """
        self._store = store
        self._embedding_client = embedding_client
        self._collection_name = collection_name
        self._dimension = dimension
        self._distance_metric = distance_metric
        self._collection: PgVectorCollection | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Ensure the vector collection (table) exists and cache the handle.

        Safe to call multiple times — uses ``CREATE TABLE IF NOT EXISTS`` under
        the hood via ``PgVectorStore.create_collection()``.
        """
        exists = await self._store.collection_exists(self._collection_name)
        if not exists:
            await self._store.create_collection(
                CollectionConfig(
                    name=self._collection_name,
                    dimension=self._dimension,
                    distance_metric=self._distance_metric,
                    index_type=IndexType.HNSW,
                )
            )
            logger.info(
                "vector_collection_created",
                collection=self._collection_name,
                dimension=self._dimension,
            )
        self._collection = await self._store.get_collection(self._collection_name)
        logger.info("vector_collection_ready", collection=self._collection_name)

    async def close(self) -> None:
        """Release the embedding client's HTTP session."""
        await self._embedding_client.close()

    # ------------------------------------------------------------------
    # DocumentVectorStoreProtocol
    # ------------------------------------------------------------------

    async def add(
        self,
        documents: list[DocumentProtocol],
    ) -> Result[list[str], VectorError]:
        """Embed and store documents in the vector collection.

        Documents with a pre-computed ``.embedding`` field skip the API call.
        Documents without an ``id`` receive a generated UUID.

        Args:
            documents: Documents to embed and store.

        Returns:
            ``Ok(list[str])`` with the stored document IDs, or
            ``Err(VectorUpsertError)`` on failure.
        """
        if not documents:
            return Ok([])

        collection = self._require_collection()
        if collection is None:
            return Err(
                VectorUpsertError("Collection not initialised — call connect() first")
            )

        try:
            records = await self._documents_to_records(documents)
            await collection.upsert(records)
            ids = [r.id for r in records]
            logger.info(
                "vector_add_complete", count=len(ids), collection=self._collection_name
            )
            return Ok(ids)
        except Exception as exc:  # noqa: BLE001 — adapter boundary: translates all store errors to domain Result
            logger.error(
                "vector_add_failed", error=str(exc), collection=self._collection_name
            )
            return Err(VectorUpsertError(str(exc)))

    async def batch_upsert(
        self,
        documents: list[DocumentProtocol],
        batch_size: int = 100,
    ) -> Result[int, VectorError]:
        """Upsert documents in batches to avoid overwhelming the embedding API.

        Args:
            documents: Documents to embed and store.
            batch_size: Documents per batch.

        Returns:
            ``Ok(int)`` total count upserted, or ``Err(VectorUpsertError)`` on failure.
        """
        total = 0
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            result = await self.add(batch)
            if result.is_err():
                return Err(result.unwrap_err())
            total += len(result.unwrap())
        return Ok(total)

    async def search(
        self,
        query: list[float],
        *,
        top_k: int = 10,
        filters: MetadataFilter | None = None,
        score_threshold: float | None = None,
    ) -> Result[list[SearchResultProtocol], VectorError]:
        """Search using a pre-computed query vector.

        Args:
            query: Query embedding vector.
            top_k: Maximum results to return.
            filters: Optional metadata filter (``MetadataFilter`` from contracts).
            score_threshold: Minimum similarity score (0–1 for cosine).

        Returns:
            ``Ok(list[RAGSearchResult])`` or ``Err(VectorSearchError)``.
        """
        collection = self._require_collection()
        if collection is None:
            return Err(
                VectorSearchError("Collection not initialised — call connect() first")
            )

        try:
            search_query = SearchQuery(
                vector=query,
                top_k=top_k,
                filter=filters,
            )
            rows = await collection.search(search_query)
            results = self._rows_to_rag_results(rows, score_threshold)
            return Ok(results)  # type: ignore[arg-type]
        except Exception as exc:  # noqa: BLE001 — adapter boundary: translates all store errors to domain Result
            logger.error("vector_search_failed", error=str(exc))
            return Err(VectorSearchError(str(exc)))

    async def search_text(
        self,
        query: str,
        *,
        top_k: int = 10,
        filters: MetadataFilter | None = None,
    ) -> Result[list[SearchResultProtocol], VectorError]:
        """Embed query text then perform similarity search.

        Args:
            query: Natural language query string.
            top_k: Maximum results to return.
            filters: Optional metadata filter.

        Returns:
            ``Ok(list[RAGSearchResult])`` or ``Err(VectorSearchError)``.
        """
        try:
            vectors = await self._embedding_client.embed([query])
            query_vector = vectors[0]
        except Exception as exc:  # noqa: BLE001 — adapter boundary: translates embedding errors to domain Result
            logger.error("query_embedding_failed", error=str(exc))
            return Err(VectorSearchError(f"Failed to embed query: {exc}"))

        return await self.search(query_vector, top_k=top_k, filters=filters)

    async def delete(self, ids: list[str]) -> Result[int, VectorError]:
        """Delete documents by ID.

        Args:
            ids: Document IDs to remove.

        Returns:
            ``Ok(int)`` count deleted, or ``Err(VectorError)`` on failure.
        """
        collection = self._require_collection()
        if collection is None:
            return Err(VectorError("Collection not initialised — call connect() first"))
        try:
            result = await collection.delete(ids)
            return Ok(result.deleted_count)
        except Exception as exc:  # noqa: BLE001 — adapter boundary: translates all store errors to domain Result
            logger.error("vector_delete_failed", error=str(exc))
            return Err(VectorError(str(exc)))

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check both the vector store and embedding client health.

        Args:
            timeout: Timeout for each check.

        Returns:
            Aggregated ``HealthCheckResult``.
        """
        store_health = await self._store.health_check(timeout=timeout)
        embed_health = await self._embedding_client.health_check(timeout=timeout)

        if store_health.is_healthy() and embed_health.is_healthy():
            status = HealthStatus.HEALTHY
        elif store_health.is_healthy() or embed_health.is_healthy():
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.UNHEALTHY

        return HealthCheckResult(
            component="vector_store_adapter",
            status=status,
            details={
                "vector_store": store_health.status.value,
                "embedding_client": embed_health.status.value,
                "collection": self._collection_name,
            },
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _require_collection(self) -> PgVectorCollection | None:
        """Return the collection or None if connect() was not yet called."""
        return self._collection

    async def _documents_to_records(
        self,
        documents: list[DocumentProtocol],
    ) -> list[VectorRecord]:
        """Convert documents to VectorRecords, generating embeddings where needed.

        Documents that already have a pre-computed embedding (``Document.embedding``)
        skip the API call. All others are embedded in one batched request.
        """
        needs_embed: list[tuple[int, DocumentProtocol]] = []
        records: list[VectorRecord | None] = [None] * len(documents)

        for idx, doc in enumerate(documents):
            embedding: list[float] | None = getattr(doc, "embedding", None)
            if embedding is not None:
                records[idx] = VectorRecord(
                    id=doc.id or str(uuid.uuid4()),
                    vector=embedding,
                    metadata=dict(doc.metadata) if doc.metadata else {},
                    content=doc.text,
                )
            else:
                needs_embed.append((idx, doc))

        if needs_embed:
            texts = [doc.text for _, doc in needs_embed]
            vectors = await self._embedding_client.embed(texts)
            for (idx, doc), vector in zip(needs_embed, vectors, strict=False):
                records[idx] = VectorRecord(
                    id=doc.id or str(uuid.uuid4()),
                    vector=vector,
                    metadata=dict(doc.metadata) if doc.metadata else {},
                    content=doc.text,
                )

        return [r for r in records if r is not None]

    def _rows_to_rag_results(
        self,
        rows: list[Any],
        score_threshold: float | None,
    ) -> list[RAGSearchResult]:
        """Convert pgvector SearchResult rows to RAGSearchResult objects.

        Args:
            rows: ``SearchResult`` objects from ``PgVectorCollection.search()``.
                  Fields: id, score, metadata, content.
            score_threshold: If set, filter out results below this score.

        Returns:
            Filtered, ordered list of RAGSearchResult.
        """
        results: list[RAGSearchResult] = []
        rank = 0
        for row in rows:
            score: float = float(row.score)
            if score_threshold is not None and score < score_threshold:
                continue
            metadata: dict[str, Any] = dict(row.metadata) if row.metadata else {}
            results.append(
                RAGSearchResult(
                    document=Document(
                        id=row.id,
                        text=row.content or "",
                        metadata=metadata,
                    ),
                    score=score,
                    rank=rank,
                    metadata=metadata,
                )
            )
            rank += 1
        return results


__all__ = ["DocumentVectorStoreAdapter"]
