"""RAG pipeline module for dependency injection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.ai.rag import (
    RAGPipelineProtocol,
    RetrievalStrategyProtocol,
)
from lexigram.di.module import DynamicModule, Module, module

if TYPE_CHECKING:
    from lexigram.ai.rag.config import RAGConfig


@module()
class RAGModule(Module):
    """Retrieval-Augmented Generation (RAG) pipeline integration.

    Call :meth:`configure` to register the RAG pipeline, strategy registries,
    and supporting services (knowledge graph, HyDE, compression, reasoning)
    for injection.

    Usage::

        from lexigram.ai.rag.config import RAGConfig

        @module(
            imports=[
                RAGModule.configure(RAGConfig(chunk_size=512))
            ]
        )
        class AppModule(Module):
            pass

    Error Handling::

        RAG pipeline failures surface as typed exceptions that can be caught
        directly or handled via the Result pattern::

            from lexigram.ai.rag.exceptions import (
                RAGError,           # base — catch-all
                PreprocessingError, # document preprocessing failure
                RetrievalError,     # retrieval / vector-store failure
                SynthesisError,     # response synthesis failure
                ChunkingError,      # document chunking failure
            )

    Exports:
        :class:`~lexigram.contracts.ai.rag.RAGPipelineProtocol`,
        :class:`~lexigram.contracts.ai.rag.RetrievalStrategyProtocol`,
        :class:`~lexigram.ai.rag.exceptions.RAGError`,
        :class:`~lexigram.ai.rag.exceptions.PreprocessingError`,
        :class:`~lexigram.ai.rag.exceptions.RetrievalError`,
        :class:`~lexigram.ai.rag.exceptions.SynthesisError`,
        :class:`~lexigram.ai.rag.exceptions.ChunkingError`
    """

    @classmethod
    def configure(cls, config: RAGConfig | None = None) -> DynamicModule:
        """Create a RAGModule with explicit configuration.

        Args:
            config: :class:`~lexigram.ai.rag.config.RAGConfig` or ``None``
                to use defaults (reads from environment variables).

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.ai.rag.di.provider import RAGProvider

        return DynamicModule(
            module=cls,
            providers=[RAGProvider(config=config)],
            exports=[
                RAGPipelineProtocol,
                RetrievalStrategyProtocol,
            ],
        )

    @classmethod
    def stub(cls, config: RAGConfig | None = None) -> DynamicModule:
        """Create a RAGModule suitable for unit and integration testing.

        Uses in-memory or no-op implementations with minimal side effects.

        Args:
            config: Optional config override. Uses safe test defaults when None.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.ai.rag.di.provider import RAGProvider

        return DynamicModule(
            module=cls,
            providers=[RAGProvider(config=config)],
            exports=[
                RAGPipelineProtocol,
                RetrievalStrategyProtocol,
            ],
        )


__all__ = ["RAGModule"]
