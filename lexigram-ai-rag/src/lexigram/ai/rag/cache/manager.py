from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from lexigram.contracts import CacheBackendProtocol

from lexigram.ai.rag.cache.base import RAGCacheConfig
from lexigram.ai.rag.cache.keys import CacheKeyBuilder
from lexigram.ai.rag.cache.stats import RAGCacheStats
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class RAGCache:
    """Caching layer for RAG operations delegating to platform CacheBackendProtocol."""

    def __init__(
        self, backend: CacheBackendProtocol, config: RAGCacheConfig | None = None
    ):
        """Initialize RAG cache.

        Args:
            backend: The platform's cache backend
            config: Optional configuration
        """
        self.backend = backend
        self.config = config or RAGCacheConfig()
        self._stats = RAGCacheStats()

    async def cache_embedding(
        self,
        text: str,
        model: str,
        embedding: list[float],
    ) -> None:
        """Cache an embedding vector."""
        key = CacheKeyBuilder.build_embedding_key(text, model, self.config.key_prefix)
        result = await self.backend.set(
            key,
            embedding,
            ttl=self.config.embedding_ttl,
        )
        if result:
            self._stats.sets += 1

    async def get_embedding(
        self,
        text: str,
        model: str,
    ) -> list[float] | None:
        """Get cached embedding vector."""
        key = CacheKeyBuilder.build_embedding_key(text, model, self.config.key_prefix)
        value = cast("Any | None", await self.backend.get(key))

        if value is None:
            self._stats.misses += 1
            return None

        self._stats.hits += 1
        return value

    async def cache_retrieval(
        self,
        query: str,
        results: list[dict[str, Any]],
        params: dict[str, Any] | None = None,
    ) -> None:
        """Cache retrieval results."""
        key = CacheKeyBuilder.build_retrieval_key(query, params, self.config.key_prefix)
        result = await self.backend.set(
            key,
            results,
            ttl=self.config.retrieval_ttl,
        )
        if result:
            self._stats.sets += 1

    async def get_retrieval(
        self,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]] | None:
        """Get cached retrieval results."""
        key = CacheKeyBuilder.build_retrieval_key(query, params, self.config.key_prefix)
        value = cast("Any | None", await self.backend.get(key))

        if value is None:
            self._stats.errors += 1
            return None

        self._stats.hits += 1
        return value

    async def cache_document(
        self,
        doc_id: str,
        document: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> None:
        """Cache a preprocessed document."""
        key = CacheKeyBuilder.build_document_key(doc_id, config, self.config.key_prefix)
        result = await self.backend.set(
            key,
            document,
            ttl=self.config.document_ttl,
        )
        if result:
            self._stats.sets += 1

    async def get_document(
        self,
        doc_id: str,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Get cached preprocessed document."""
        key = CacheKeyBuilder.build_document_key(doc_id, config, self.config.key_prefix)
        value = cast("Any | None", await self.backend.get(key))

        if value is None:
            self._stats.errors += 1
            return None

        self._stats.hits += 1
        return value

    async def cache_reranking(
        self,
        query: str,
        document_ids: list[str],
        model: str,
        scores: list[float],
    ) -> None:
        """Cache reranking results."""
        key = CacheKeyBuilder.build_reranking_key(
            query,
            document_ids,
            model,
            self.config.key_prefix,
        )
        result = await self.backend.set(
            key,
            scores,
            ttl=self.config.reranking_ttl,
        )
        if result:
            self._stats.sets += 1

    async def get_reranking(
        self,
        query: str,
        document_ids: list[str],
        model: str,
    ) -> list[float] | None:
        """Get cached reranking scores."""
        key = CacheKeyBuilder.build_reranking_key(
            query,
            document_ids,
            model,
            self.config.key_prefix,
        )
        value = cast("Any | None", await self.backend.get(key))

        if value is None:
            self._stats.errors += 1
            return None

        self._stats.hits += 1
        return value

    async def cache_query_transformation(
        self,
        query: str,
        transformation_type: str,
        transformed: str | list[str],
        params: dict[str, Any] | None = None,
    ) -> None:
        """Cache query transformation results."""
        key = CacheKeyBuilder.build_query_transformation_key(
            query,
            transformation_type,
            params,
            self.config.key_prefix,
        )
        result = await self.backend.set(
            key,
            transformed,
            ttl=self.config.query_transformation_ttl,
        )
        if result:
            self._stats.sets += 1

    async def get_query_transformation(
        self,
        query: str,
        transformation_type: str,
        params: dict[str, Any] | None = None,
    ) -> str | list[str] | None:
        """Get cached query transformation."""
        key = CacheKeyBuilder.build_query_transformation_key(
            query,
            transformation_type,
            params,
            self.config.key_prefix,
        )
        value = cast("Any | None", await self.backend.get(key))

        if value is None:
            self._stats.errors += 1
            return None

        self._stats.hits += 1
        return value

    async def invalidate(self, key: str) -> bool:
        """Invalidate a specific cache entry."""
        result = await self.backend.delete(key)
        if result:
            self._stats.deletes += 1
            return True
        return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching a pattern."""
        if hasattr(self.backend, "invalidate_pattern"):
            result = await self.backend.invalidate_pattern(pattern)
            if result:
                count = result
                self._stats.deletes += count
                return count

        logger.warning(
            "Pattern-based invalidation not supported by CacheBackendProtocol"
        )
        return 0

    async def clear(self) -> None:
        """Clear all cache entries."""
        await self.backend.clear()
        self._stats.deletes += 1

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total_entries = 0
        if hasattr(self.backend, "_data"):
            total_entries = len(self.backend._data)

        return {
            "hits": self._stats.hits,
            "misses": self._stats.misses,
            "sets": self._stats.sets,
            "deletes": self._stats.deletes,
            "errors": self._stats.errors,
            "hit_rate": self._stats.hit_rate,
            "total_operations": self._stats.total_operations,
            "total_entries": total_entries,
        }

    async def cleanup_expired(self) -> int:
        """Remove expired entries from cache (handled by backend)."""
        return 0
