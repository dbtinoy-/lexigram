"""Factory for creating AI-layer vector store instances.

Wraps an infra ``VectorStoreProtocol`` (from lexigram-vector) in a
``VectorStoreAdapter``, adding embedding generation and document-level
type-bridging. Falls back to ``MockVectorStore`` when no infra store
is available (testing / standalone scenarios).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.data.vector.protocols import (
        VectorStoreProtocol as InfraVectorStoreProtocol,
    )
    from lexigram.contracts.infra.cache import CacheBackendProtocol
    from lexigram.vector.config import VectorConfig

logger = get_logger(__name__)

EmbeddingFn = Callable[[list[str]], Awaitable[list[list[float]]]]


async def create_vector_store(
    config: VectorConfig,
    *,
    infra_store: InfraVectorStoreProtocol | None = None,
    cache_backend: CacheBackendProtocol | None = None,
    embedding_fn: EmbeddingFn | None = None,
) -> Any:
    """Create an AI-layer vector store, delegating to the infra store when available.

    When ``infra_store`` is provided (registered by lexigram-vector's provider),
    a :class:`~lexigram.vector.adapters.vector_store.VectorStoreAdapter` is returned
    that wraps it. Otherwise, a
    :class:`~lexigram.vector.testing.mocks.MockVectorStore` is returned — suitable
    for testing and environments without an infra store.

    Args:
        config: Vector configuration block.
        infra_store: Infra-level vector store (from lexigram-vector), if present.
        cache_backend: Platform cache backend for embedding caching.
        embedding_fn: Async callable ``(texts) -> list[list[float]]`` for embedding.

    Returns:
        A configured vector store instance satisfying the AI-layer protocol.
    """
    embedding_cache = None
    if config.enable_cache and cache_backend:
        from lexigram.vector.embedding.cache import EmbeddingCache

        embedding_cache = EmbeddingCache(
            cache_service=cache_backend,
            ttl=config.cache_ttl,
            key_prefix=f"embedding:{config.collection_name}:",
        )
        logger.info("Embedding cache enabled (TTL: %ds)", config.cache_ttl)

    if infra_store is not None:
        from lexigram.vector.adapters.vector_store import VectorStoreAdapter

        return VectorStoreAdapter(
            infra_store=infra_store,
            collection_name=config.collection_name,
            dimension=config.default_dimension,
            config=config,
            embedding_cache=embedding_cache,
            embedding_fn=embedding_fn,
        )

    if config.backend != "mock":
        logger.warning(
            "create_vector_store: no infra VectorStoreProtocol found for backend %r; "
            "falling back to MockVectorStore. "
            "Add lexigram-vector's VectorModule to your app to use a real backend.",
            config.backend,
        )

    from lexigram.vector.testing.mocks import MockVectorStore

    return MockVectorStore(config)


__all__ = [
    "create_vector_store",
]
