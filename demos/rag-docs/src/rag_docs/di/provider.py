"""DI wiring for the rag-docs demo — the **provider lifecycle** lesson.

``DocsAskProvider`` is the demo's sole custom provider.  It owns two jobs:

1. **register()** — bind the ask service and controller as lazy singletons.
   The factory methods defer resolution until ``boot()`` has assembled
   everything.

2. **boot()** — the heavy lifting: ingest the markdown corpus, fit the
   embedder's IDF weights, upsert vector records, and assemble the
   ``DocsAskService`` with retrieval strategies and a synthesizer.

``resolve_default_docs_dir()`` is CWD-proof: it anchors to this file's
location (``di/provider.py`` → ``[5]`` parents up = repository root) so
tests
and standalone server launches work from any invocation point.

Register/boot pattern (auth-rbac style)::

    container.singleton(DocsAskService, factory=self._get_service)
    container.singleton(DocsAskApiController, factory=self._build_controller)

...so framework code resolves the protocol while tests can import the
concrete class.
"""

from __future__ import annotations

from pathlib import Path

from lexigram.ai.rag.synthesis.synthesizers.extractive import (
    ExtractiveSynthesizer,
)
from lexigram.contracts.core.di import (
    ContainerRegistrarProtocol,
    ContainerResolverProtocol,
)
from lexigram.contracts.core.health import (
    HealthCheckResult,
)
from lexigram.di.provider import Provider
from rag_docs.controllers.api import DocsAskApiController
from rag_docs.repository.embedder import HashingEmbedder
from rag_docs.repository.index_builder import build_docs_store
from rag_docs.services.docs_ask import DocsAskService, strategies_snapshot


class DocsAskProvider(Provider):
    """Build the docs index at boot and register the ask service.

    This is the **provider lifecycle** pattern: ``register()`` binds
    contracts to lazy factories, ``boot()`` runs post-registration setup
    (corpus ingestion, embedder fitting, service assembly), and
    ``shutdown()`` cleans up.

    The provider is stateful across the lifecycle (``_service`` is set
    during boot) but stateless per request — each ask is independent.
    """

    name = "rag-docs"

    def __init__(self, docs_dir: Path | None = None) -> None:
        super().__init__()
        self._docs_dir = docs_dir
        self._service: DocsAskService | None = None

    def _get_service(self) -> DocsAskService:
        """Return the service assembled during boot.

        Raises:
            RuntimeError: If called before ``boot()`` has run.
        """
        if self._service is None:
            raise RuntimeError("DocsAskProvider has not been booted yet")
        return self._service

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind the lazy service factory; collaborators resolve in boot.

        Pattern: ``container.singleton(Contract, factory=self._getter)``
        so the framework resolves the instance lazily on first access.
        """
        container.singleton(DocsAskService, factory=self._get_service)
        container.singleton(DocsAskApiController, factory=self._build_controller)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Ingest the corpus and assemble DocsAskService.

        The boot sequence:
        1. Resolve the corpus directory (configured path or CWD-proof default)
        2. Create a shared ``HashingEmbedder`` — one instance for both
           corpus indexing and query embedding so IDF weights match
        3. ``build_docs_store`` walks markdown files, chunks, fits IDF,
           embeds, and upserts into a ``MemoryVectorCollection``
        4. Assemble ``DocsAskService`` with the collection, embedder,
           extractive synthesizer, and pre-built strategy registry
        """
        docs_dir = self._docs_dir or resolve_default_docs_dir()
        # One shared embedder: build_docs_store fits it on the corpus, then
        # the service reuses it so query vectors use the same IDF weights.
        embedder = HashingEmbedder()
        _, collection, stats = await build_docs_store(docs_dir, embedder)
        self._service = DocsAskService(
            collection=collection,
            embedder=embedder,
            synthesizer=ExtractiveSynthesizer(max_sentences=4),
            strategies=strategies_snapshot(),
            stats=stats,
        )

    async def _build_controller(
        self, container: ContainerResolverProtocol
    ) -> DocsAskApiController:
        """Factory: resolve the service and inject into the controller."""
        return DocsAskApiController(service=await container.resolve(DocsAskService))

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report docs index readiness."""
        return HealthCheckResult(
            component=self.name,
            details={"docs_dir": str(self._docs_dir)},
        )


def resolve_default_docs_dir() -> Path:
    """Return the repository's real docs directory.

    Resolution is anchored to this file's location (never the process CWD):
    parents are ``[0] di``, ``[1] rag_docs``, ``[2] src``, ``[3] rag-docs``,
    ``[4] demos``, ``[5] repository root``.
    """
    return Path(__file__).resolve().parents[5] / "docs"


__all__ = ["DocsAskProvider", "resolve_default_docs_dir"]
