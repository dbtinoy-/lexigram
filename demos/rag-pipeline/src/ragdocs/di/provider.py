"""Provider wiring for the RAG pipeline demo.

Convention followed: **Provider pattern** — ``RagDocsProvider`` is the
canonical shape (mirrors ``lexigram-auth`` + the boot-phase ``bind()``
contract in ``lexigram.contracts.core.di``):

- ``register()`` only *declares* bindings.  Zero-arg factories cover
  purely config-derived services; dependency-full services are declared
  as class bindings and instantiated in :meth:`boot`.
- ``boot()`` resolves cross-module dependencies after every provider
  has registered and rebinds the concrete instances via
  ``container.bind()``.
- Controllers are constructed by the router from the container; ``boot``
  binds their prebuilt instances so per-request resolution reuses them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.core.health import (
    HealthCheckCategory,
    HealthCheckResult,
    HealthStatus,
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
    """Bind the RAG pipeline services as container-managed singletons."""

    name = "ragdocs"

    config_key: str | None = "ragdocs"
    config_model: type | None = RagDocsConfig

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Declare bindings; concrete wiring happens in :meth:`boot`."""
        cfg = self.config or RagDocsConfig()

        container.singleton(RagDocsConfig, instance=cfg)

        # Class bindings so the keys exist; boot() replaces them with
        # fully-wired instances via container.bind().
        container.singleton(RagApiController, RagApiController)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Resolve cross-module dependencies and bind concrete instances."""
        from ragdocs.services.chunker import DocumentChunker
        from ragdocs.services.retriever import Retriever
        from ragdocs.vector_store import InMemoryVectorStore

        cfg = await container.resolve(RagDocsConfig)

        # Create the vector store
        vector_store = InMemoryVectorStore(dimension=cfg.embedding_dimension)

        # Create the chunker and retriever
        chunker = DocumentChunker(chunk_size=cfg.chunk_size)
        retriever = Retriever(vector_store=vector_store, top_k=cfg.top_k)

        # Bind the wired controller
        container.bind(
            RagApiController,
            RagApiController(vector_store=vector_store, chunker=chunker, retriever=retriever),
        )

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report readiness of the RAG pipeline."""
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            category=HealthCheckCategory.READINESS,
        )
