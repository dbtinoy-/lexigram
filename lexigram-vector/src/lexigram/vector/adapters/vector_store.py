"""Vector store adapter — bridges infra VectorCollectionProtocol to AI VectorStoreProtocol.

Wraps a ``VectorCollectionProtocol`` (provided by lexigram-vector) with AI-layer
concerns: embedding generation, ``Document`` ↔ ``VectorRecord`` conversion, and
``Result``-typed error handling. The infra layer owns connections; this layer
owns document semantics.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from lexigram.contracts.ai.vector import Document, RAGSearchResult
from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.contracts.data.vector.filters import (
    FilterOperator,
    LogicalOperator,
    MetadataCondition,
    MetadataConditionGroup,
)
from lexigram.contracts.data.vector.types import (
    CollectionConfig,
    SearchQuery,
    VectorRecord,
)
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result
from lexigram.vector.exceptions import VectorError as VectorStoreError
from lexigram.vector.types import Embedding

SearchResult = RAGSearchResult

if TYPE_CHECKING:
    from lexigram.contracts.data.vector.protocols import VectorCollectionProtocol
    from lexigram.contracts.data.vector.protocols import (
        VectorStoreProtocol as InfraVectorStoreProtocol,
    )
    from lexigram.vector.config import VectorConfig
    from lexigram.vector.embedding.cache import EmbeddingCache

logger = get_logger(__name__)

EmbeddingFn = Callable[[list[str]], Awaitable[list[list[float]]]]


class VectorStoreAdapter:
    """Adapts infra ``VectorCollectionProtocol`` to AI ``VectorStoreProtocol``.

    Receives a ``VectorStoreProtocol`` from lexigram-vector via constructor injection.
    Collection access is lazy — ``get_collection`` is called on the first vector
    operation so this class is safe to construct before the infra store has booted.

    Embedding generation is delegated to an optional ``embedding_fn``
    (typically ``EmbeddingClientProtocol.embed``). When ``embedding_fn`` is ``None``,
    ``add()`` requires ``doc.embedding`` to be pre-set and ``search_text()`` returns
    an error.
    """

    def __init__(
        self,
        infra_store: InfraVectorStoreProtocol,
        collection_name: str,
        dimension: int,
        config: VectorConfig,
        embedding_cache: EmbeddingCache | None = None,
        embedding_fn: EmbeddingFn | None = None,
    ) -> None:
        """Initialize the adapter.

        Args:
            infra_store: Infra-level vector store (from lexigram-vector's provider).
            collection_name: Name of the target vector collection.
            dimension: Vector dimensionality, used when creating the collection.
            config: Vector configuration block.
            embedding_cache: Optional cache for generated embeddings.
            embedding_fn: Optional async callable ``(texts) -> list[list[float]]``.
        """
        self._infra_store = infra_store
        self._collection_name = collection_name
        self._dimension = dimension
        self._config = config
        self._embedding_cache = embedding_cache
        self._embedding_fn = embedding_fn
        self._collection: VectorCollectionProtocol | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _ensure_collection(self) -> VectorCollectionProtocol:
        """Return the collection handle, creating the collection if needed.

        Raises any infrastructure exception directly — callers must catch.
        """
        if self._collection is None:
            if not await self._infra_store.collection_exists(self._collection_name):
                await self._infra_store.create_collection(
                    CollectionConfig(
                        name=self._collection_name,
                        dimension=self._dimension,
                    )
                )
            self._collection = await self._infra_store.get_collection(
                self._collection_name
            )
        return self._collection

    async def _embed_texts(self, texts: list[str]) -> list[list[float]] | None:
        """Generate embeddings for ``texts``, using the cache when available.

        Returns ``None`` when no ``embedding_fn`` is configured.
        """
        if not self._embedding_fn:
            return None

        cache = self._embedding_cache if self._config.enable_cache else None
        model = self._config.embedding_model

        if not cache:
            return await self._embedding_fn(texts)

        # Per-text cache lookup — avoid re-embedding already-cached texts.
        results: list[list[float] | None] = [None] * len(texts)
        uncached_idx: list[int] = []
        uncached_texts: list[str] = []

        for i, text in enumerate(texts):
            cached = await cache.get(text, model)
            if cached is not None:
                if isinstance(cached, Embedding):
                    results[i] = list(cached.vector)
                else:
                    results[i] = list(cached)
            else:
                uncached_idx.append(i)
                uncached_texts.append(text)

        if uncached_texts:
            fresh = await self._embedding_fn(uncached_texts)
            for list_pos, (text, emb) in zip(
                uncached_idx, zip(uncached_texts, fresh, strict=False), strict=False
            ):
                results[list_pos] = emb
                await cache.set(text, emb, model)

        return [e for e in results if e is not None]

    def _build_filter(
        self, filters: dict[str, Any]
    ) -> MetadataCondition | MetadataConditionGroup:
        """Convert a flat key-value dict to an infra-compatible ``MetadataFilter``.

        Single-key dicts produce a ``MetadataCondition``; multi-key dicts produce
        an AND-grouped ``MetadataConditionGroup``.

        Args:
            filters: Metadata equality conditions.

        Returns:
            A ``MetadataCondition`` or ``MetadataConditionGroup``.
        """
        conditions = tuple(
            MetadataCondition(field=k, operator=FilterOperator.EQ, value=v)
            for k, v in filters.items()
        )
        if len(conditions) == 1:
            return conditions[0]
        return MetadataConditionGroup(
            logical_operator=LogicalOperator.AND,
            conditions=conditions,
        )

    # ------------------------------------------------------------------
    # VectorStoreProtocol (AI-level) implementation
    # ------------------------------------------------------------------

    async def add(
        self, documents: list[Document]
    ) -> Result[list[str], VectorStoreError]:
        """Add documents to the vector store.

        Documents without ``embedding`` will be embedded via ``embedding_fn`` if
        provided; otherwise an ``Err`` is returned.

        Args:
            documents: Documents to add. Must each have ``text`` set.

        Returns:
            ``Ok(list[str])`` with document IDs, or ``Err(VectorStoreError)``.
        """
        try:
            collection = await self._ensure_collection()
        except (ConnectionError, OSError, ValueError, RuntimeError) as e:
            return Err(VectorStoreError(f"Collection initialisation failed: {e}"))

        try:
            # Identify docs that need embeddings generated.
            need_embed = [doc for doc in documents if not doc.embedding]
            emb_map: dict[int, list[float]] = {}

            if need_embed:
                generated = await self._embed_texts([d.text for d in need_embed])
                if generated is None:
                    return Err(
                        VectorStoreError(
                            "Documents have no embedding and no EmbeddingClientProtocol is "
                            "configured. Set doc.embedding or provide an embedding client."
                        )
                    )
                ni = 0
                for i, doc in enumerate(documents):
                    if not doc.embedding:
                        emb_map[i] = generated[ni]
                        ni += 1

            records: list[VectorRecord] = []
            ids: list[str] = []

            for i, doc in enumerate(documents):
                doc_id = doc.id or str(uuid4())
                ids.append(doc_id)
                vector = doc.embedding if doc.embedding else emb_map[i]
                records.append(
                    VectorRecord(
                        id=doc_id,
                        vector=vector,
                        metadata=doc.metadata or {},
                        content=doc.text,
                    )
                )

            await collection.upsert(records)
            return Ok(ids)

        except (ConnectionError, OSError, ValueError, RuntimeError) as e:
            return Err(VectorStoreError(f"Failed to add documents: {e}"))

    async def batch_upsert(
        self,
        documents: list[Document],
        batch_size: int = 100,
    ) -> Result[int, VectorStoreError]:
        """Upsert documents in fixed-size batches.

        Args:
            documents: Documents to upsert.
            batch_size: Documents per batch.

        Returns:
            ``Ok(int)`` with total upserted count, or ``Err(VectorStoreError)``.
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
        filters: dict[str, Any] | None = None,
        score_threshold: float | None = None,
    ) -> Result[list[SearchResult], VectorStoreError]:
        """Search for similar documents using a pre-computed query vector.

        Args:
            query: Query embedding vector.
            top_k: Maximum number of results.
            filters: Metadata equality filters.
            score_threshold: Minimum similarity score to include.

        Returns:
            ``Ok(list[SearchResult])`` ordered by similarity, or ``Err(VectorStoreError)``.
        """
        try:
            collection = await self._ensure_collection()
        except (ConnectionError, OSError, ValueError, RuntimeError) as e:
            return Err(VectorStoreError(f"Collection initialisation failed: {e}"))

        try:
            infra_filter = self._build_filter(filters) if filters else None
            query_obj = SearchQuery(
                vector=query,
                top_k=top_k,
                filter=infra_filter,
                min_score=score_threshold,
            )
            infra_results = await collection.search(query_obj)

            ai_results: list[SearchResult] = [
                SearchResult(
                    document=Document(
                        id=r.id,
                        text=r.content or "",
                        metadata=r.metadata or {},
                    ),
                    score=r.score,
                    rank=rank,
                )
                for rank, r in enumerate(infra_results)
            ]
            return Ok(ai_results)

        except (ConnectionError, OSError, ValueError, RuntimeError) as e:
            return Err(VectorStoreError(f"Search failed: {e}"))

    async def search_text(
        self,
        query: str,
        *,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> Result[list[SearchResult], VectorStoreError]:
        """Search for similar documents using a text query.

        Embeds ``query`` via ``embedding_fn`` then delegates to :meth:`search`.

        Args:
            query: Query text to embed and search.
            top_k: Maximum number of results.
            filters: Metadata equality filters.

        Returns:
            ``Ok(list[SearchResult])`` on success, or ``Err(VectorStoreError)`` if
            no ``embedding_fn`` is configured.
        """
        embedded = await self._embed_texts([query])
        if embedded is None:
            return Err(
                VectorStoreError(
                    "search_text requires an EmbeddingClientProtocol. "
                    "Provide one via the VectorProvider."
                )
            )
        return await self.search(embedded[0], top_k=top_k, filters=filters)

    async def delete(self, ids: list[str]) -> Result[int, VectorStoreError]:
        """Delete documents by ID.

        Args:
            ids: Document IDs to delete.

        Returns:
            ``Ok(int)`` with deletion count, or ``Err(VectorStoreError)``.
        """
        try:
            collection = await self._ensure_collection()
        except (ConnectionError, OSError, ValueError, RuntimeError) as e:
            return Err(VectorStoreError(f"Collection initialisation failed: {e}"))

        try:
            result = await collection.delete(ids)
            return Ok(result.deleted_count)
        except (ConnectionError, OSError, ValueError, RuntimeError) as e:
            return Err(VectorStoreError(f"Delete failed: {e}"))

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Perform a health check by querying the collection document count.

        Returns:
            Structured health check result.
        """
        try:
            collection = await self._ensure_collection()
            count = await collection.count()
            return HealthCheckResult(
                component="vector.adapter",
                status=HealthStatus.HEALTHY,
                details={
                    "collection": self._collection_name,
                    "vector_count": count,
                },
            )
        except (ConnectionError, OSError, ValueError, RuntimeError) as e:
            return HealthCheckResult(
                component="vector.adapter",
                status=HealthStatus.UNHEALTHY,
                error=str(e),
                details={"collection": self._collection_name},
            )


__all__ = ["VectorStoreAdapter"]
