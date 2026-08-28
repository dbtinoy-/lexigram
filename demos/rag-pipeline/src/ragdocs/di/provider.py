"""Lifecycle wiring for the single-purpose RAG retrieval demo.

The demo owns document chunking and a deterministic local embedder.  Lexigram
owns vector-store lifecycle, collection management, and similarity search.
That boundary makes the example easy to move from the in-memory backend to
Qdrant, pgvector, or another configured backend later.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.core.health import (
    HealthCheckCategory,
    HealthCheckResult,
    HealthStatus,
)
from lexigram.contracts.data.vector import (
    CollectionConfig,
    DistanceMetric,
    IndexType,
    VectorStoreProtocol,
)
from lexigram.di.provider import Provider
from ragdocs.config import RagDocsConfig
from ragdocs.controllers.api import RagApiController

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

__all__ = ["RagDocsProvider"]


class RagDocsProvider(Provider):
    """Bind the chunker, embedder, and vector collection to the app."""

    name = "ragdocs"
    config_key: str | None = "ragdocs"
    config_model: type | None = RagDocsConfig

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Declare config and controller bindings before boot resolution."""
        cfg = self.config or RagDocsConfig()
        container.singleton(RagDocsConfig, instance=cfg)
        container.singleton(RagApiController, RagApiController)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Create the configured collection and wire the controller."""
        from ragdocs.services.chunker import DocumentChunker
        from ragdocs.services.retriever import Retriever
        from ragdocs.vector_store import DeterministicEmbedder

        cfg = await container.resolve(RagDocsConfig)
        vector_store = await container.resolve(VectorStoreProtocol)

        if not await vector_store.collection_exists(cfg.collection_name):
            await vector_store.create_collection(
                CollectionConfig(
                    name=cfg.collection_name,
                    dimension=cfg.embedding_dimension,
                    distance_metric=DistanceMetric.COSINE,
                    index_type=IndexType.FLAT,
                )
            )

        collection = await vector_store.get_collection(cfg.collection_name)
        embedder = DeterministicEmbedder(cfg.embedding_dimension)
        retriever = Retriever(
            collection=collection,
            embedder=embedder,
            top_k=cfg.top_k,
        )

        container.bind(
            RagApiController,
            RagApiController(
                collection=collection,
                chunker=DocumentChunker(chunk_size=cfg.chunk_size),
                embedder=embedder,
                retriever=retriever,
            ),
        )

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report readiness for the application-owned pipeline."""
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            category=HealthCheckCategory.READINESS,
        )
