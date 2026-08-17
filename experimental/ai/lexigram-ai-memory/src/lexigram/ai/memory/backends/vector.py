"""Vector-backed memory backend — semantic search via DocumentVectorStoreProtocol."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from lexigram.ai.memory.exceptions import EmbeddingError, MemoryStoreError
from lexigram.contracts.ai.memory import (
    MemoryEntry,
    MemoryQuery,
    MemorySearchResult,
    MemoryStoreProtocol,
)
from lexigram.contracts.ai.vector import (
    Document,
    DocumentVectorStoreProtocol,
    SearchResultProtocol,
)
from lexigram.contracts.core import HealthCheckResult, HealthStatus

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class VectorMemoryBackend:
    """MemoryStoreProtocol that persists entries as vector-searchable documents."""

    def __init__(
        self,
        vector_store: DocumentVectorStoreProtocol,
        embed_fn: Callable[[str], Awaitable[list[float]]] | None = None,
        collection: str = "memory",
        fallback: MemoryStoreProtocol | None = None,
    ) -> None:
        self._vs = vector_store
        self._embed_fn = embed_fn
        self._collection = collection
        self._fallback = fallback

    async def _embed(self, text: str) -> list[float]:
        if self._embed_fn is None:
            raise EmbeddingError("No embed_fn provided — cannot produce embedding")
        return await self._embed_fn(text)

    def _to_document(self, entry: MemoryEntry) -> Document:
        metadata: dict[str, Any] = {
            "owner_id": entry.owner_id,
            "content": entry.content,
            "role": entry.role,
            "timestamp": entry.timestamp.isoformat(),
            "importance": entry.importance,
            "memory_metadata": entry.metadata,
            "collection": self._collection,
        }
        return Document(
            id=entry.id,
            text=entry.content,
            metadata=metadata,
            embedding=entry.embedding,
        )

    def _to_memory_result(
        self,
        hit: SearchResultProtocol,
        query: MemoryQuery,
    ) -> MemorySearchResult:
        metadata = hit.document.metadata
        timestamp_raw = metadata.get("timestamp", datetime.now(UTC).isoformat())
        timestamp = datetime.fromisoformat(str(timestamp_raw))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)

        entry = MemoryEntry(
            id=hit.document.id or "",
            owner_id=str(metadata.get("owner_id", "")),
            content=metadata.get("content", hit.document.text),
            role=str(metadata.get("role", "user")),
            timestamp=timestamp,
            importance=float(metadata.get("importance", 0.5)),
            metadata=cast("dict[str, Any]", metadata.get("memory_metadata", {})),
            embedding=cast(
                "list[float] | None", getattr(hit.document, "embedding", None)
            ),
        )
        combined_score = (
            query.relevance_weight * float(hit.score)
            + query.importance_weight * entry.importance
        )
        return MemorySearchResult(entry=entry, score=combined_score, source="vector")

    async def store(self, entry: MemoryEntry) -> None:
        vector = entry.embedding
        if vector is None:
            vector = await self._embed(entry.content)
        doc = self._to_document(
            MemoryEntry(
                id=entry.id,
                owner_id=entry.owner_id,
                content=entry.content,
                role=entry.role,
                timestamp=entry.timestamp,
                importance=entry.importance,
                metadata=entry.metadata,
                embedding=vector,
            )
        )
        add_result = await self._vs.add([doc])
        if add_result.is_err():
            raise MemoryStoreError(
                f"Vector add failed: {entry.id}",
                store="vector",
            ) from add_result.unwrap_err()
        if self._fallback is not None:
            await self._fallback.store(entry)

    async def retrieve(self, query: MemoryQuery) -> list[MemorySearchResult]:
        query_vector = await self._embed(query.query)
        search_result = await self._vs.search(
            query_vector,
            top_k=query.top_k,
            filters={
                "collection": self._collection,
                "owner_id": query.owner_id,
                **(query.filters or {}),
            },
        )
        if search_result.is_err():
            raise MemoryStoreError(
                "Vector search failed", store="vector"
            ) from search_result.unwrap_err()

        hits = search_result.unwrap_or([])
        results = [self._to_memory_result(hit, query) for hit in hits]
        return [result for result in results if result.score >= query.min_relevance]

    async def get_recent(self, n: int, owner_id: str) -> list[MemoryEntry]:
        if self._fallback is None:
            return []
        return await self._fallback.get_recent(n, owner_id)

    async def delete(self, entry_id: str, owner_id: str) -> None:
        delete_result = await self._vs.delete([entry_id])
        if delete_result.is_err():
            raise MemoryStoreError(
                f"Vector delete failed: {entry_id}",
                store="vector",
            ) from delete_result.unwrap_err()
        if self._fallback is not None:
            await self._fallback.delete(entry_id, owner_id)

    async def clear(self, owner_id: str) -> None:
        if self._fallback is not None:
            await self._fallback.clear(owner_id)

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        return HealthCheckResult(
            component="memory.vector",
            status=HealthStatus.HEALTHY,
            details={"collection": self._collection, "timeout": timeout},
        )


__all__ = ["VectorMemoryBackend"]
