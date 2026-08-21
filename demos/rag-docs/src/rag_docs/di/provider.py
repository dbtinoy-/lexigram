"""Provider wiring for the docs ask demo."""

from __future__ import annotations

from pathlib import Path

from lexigram.ai.rag.synthesis.synthesizers.extractive import (
    ExtractiveSynthesizer,
)
from lexigram.contracts.core.di import (
    ContainerRegistrarProtocol,
    ContainerResolverProtocol,
)
from lexigram.di.provider import Provider
from rag_docs.embedder import HashingEmbedder
from rag_docs.index_builder import build_docs_store
from rag_docs.service import STRATEGIES, DocsAskService


class DocsAskProvider(Provider):
    """Build the docs index at boot and register the ask service."""

    name = "rag-docs"

    def __init__(self, docs_dir: Path | None = None) -> None:
        super().__init__()
        self._docs_dir = docs_dir
        self._service: DocsAskService | None = None

    def _get_service(self) -> DocsAskService:
        """Return the service assembled during boot."""
        if self._service is None:
            raise RuntimeError("DocsAskProvider has not been booted yet")
        return self._service

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind the lazy service factory; collaborators resolve in boot."""
        container.singleton(DocsAskService, factory=self._get_service)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Ingest the corpus and assemble DocsAskService."""
        docs_dir = self._docs_dir or resolve_default_docs_dir()
        _, collection, stats = await build_docs_store(docs_dir, HashingEmbedder())
        self._service = DocsAskService(
            collection=collection,
            embedder=HashingEmbedder(),
            synthesizer=ExtractiveSynthesizer(max_sentences=4),
            strategies=dict(STRATEGIES),
            stats=stats,
        )


def resolve_default_docs_dir() -> Path:
    """Return the repository's real docs directory.

    Resolution is anchored to this file's location (never the process CWD):
    parents are ``[0] di``, ``[1] rag_docs``, ``[2] src``, ``[3] rag-docs``,
    ``[4] demos``, ``[5] repository root``.
    """
    return Path(__file__).resolve().parents[5] / "docs"


__all__ = ["DocsAskProvider", "resolve_default_docs_dir"]
