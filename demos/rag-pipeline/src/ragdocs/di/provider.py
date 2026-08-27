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

Lifecycle:
  1. ``register()`` — declare bindings (no resolution)
  2. ``boot()`` — resolve cross-module deps, create instances, bind
  3. ``shutdown()`` — cleanup (not needed for in-memory stores)

For full reference see:
- ``lexigram.di.provider.Provider`` — base provider class
- ``lexigram.contracts.core.di`` — container protocols
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
    """Bind the RAG pipeline services as container-managed singletons.

    This provider demonstrates the full lifecycle:
    - ``register()`` declares the config and controller bindings
    - ``boot()`` creates the vector store, chunker, and retriever
    - ``health_check()`` reports readiness status
    """

    name = "ragdocs"

    # Config binding — the framework injects the typed YAML section here
    config_key: str | None = "ragdocs"
    config_model: type | None = RagDocsConfig

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Declare bindings; concrete wiring happens in :meth:`boot`.

        This method runs AFTER the framework has loaded the config.
        ``self.config`` contains the typed ``RagDocsConfig`` instance
        with YAML values + env overrides already merged.
        """
        cfg = self.config or RagDocsConfig()

        # Bind the config as a singleton — other services can resolve it
        container.singleton(RagDocsConfig, instance=cfg)

        # Class bindings so the keys exist; boot() replaces them with
        # fully-wired instances via container.bind().
        container.singleton(RagApiController, RagApiController)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Resolve cross-module dependencies and bind concrete instances.

        This method runs AFTER all providers have registered.
        Resolution is safe — all bindings are in place.
        """
        from ragdocs.services.chunker import DocumentChunker
        from ragdocs.services.retriever import Retriever
        from ragdocs.vector_store import InMemoryVectorStore

        cfg = await container.resolve(RagDocsConfig)

        # Create the vector store
        # In production, replace with lexigram-ai-rag's backend:
        #   from lexigram_ai_rag import PineconeVectorStore, VectorConfig
        #   vector_store = PineconeVectorStore(config=VectorConfig(index="my-index"))
        vector_store = InMemoryVectorStore(dimension=cfg.embedding_dimension)

        # Create the chunker and retriever
        chunker = DocumentChunker(chunk_size=cfg.chunk_size)
        retriever = Retriever(vector_store=vector_store, top_k=cfg.top_k)

        # Bind the wired controller — the router resolves this for
        # every request, so per-request resolution reuses the same instance.
        container.bind(
            RagApiController,
            RagApiController(
                vector_store=vector_store, chunker=chunker, retriever=retriever
            ),
        )

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report readiness of the RAG pipeline.

        Called by the framework's health check system.  Return
        HEALTHY if the service is ready to handle requests.
        """
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            category=HealthCheckCategory.READINESS,
        )
