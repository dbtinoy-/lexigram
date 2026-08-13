"""RAG (Retrieval-Augmented Generation) module.

Root ``__init__.py`` exposes only the core pipeline API.
All specialised symbols remain importable from their subpackage paths, e.g.::

    from lexigram.ai.rag.evaluation import HallucinationDetector
    from lexigram.ai.rag.chunking import SemanticChunker
    from lexigram.ai.rag.hyde import SingleHyDEGenerator
"""

from __future__ import annotations

import importlib.metadata
from typing import TYPE_CHECKING, Any

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from lexigram.ai.rag.constants import __version__ as __version__

_LAZY_IMPORTS = {
    # DI Provider
    "RAGModule": "lexigram.ai.rag.module",
    "RAGProvider": "lexigram.ai.rag.di.provider",
    # Events
    "RetrievalCompletedEvent": "lexigram.ai.rag.events",
    "SynthesisCompletedEvent": "lexigram.ai.rag.events",
    # Hooks
    "RAGAnswerSynthesizedHook": "lexigram.ai.rag.hooks",
    "RAGDocumentsRetrievedHook": "lexigram.ai.rag.hooks",
    "RAGPipelineStartedHook": "lexigram.ai.rag.hooks",
    # Core types
    "Chunk": "lexigram.ai.rag.types",
    "Context": "lexigram.ai.rag.types",
    "RAGError": "lexigram.ai.rag.types",
    # Pipeline
    "RAGPipeline": "lexigram.ai.rag.pipeline",
    "PipelineBuilder": "lexigram.ai.rag.pipeline.builder",
    # Config
    "RAGConfig": "lexigram.ai.rag.config",
    "RAGTenancyConfig": "lexigram.ai.rag.config",
    "PipelineConfig": "lexigram.ai.rag.config",
    "IngestionConfig": "lexigram.ai.rag.config",
    "RetrievalConfig": "lexigram.ai.rag.config",
    "SynthesisConfig": "lexigram.ai.rag.config",
    # Chunking — factory + primary types only
    "ChunkingConfig": "lexigram.ai.rag.chunking",
    "create_chunker": "lexigram.ai.rag.chunking",
    # Cache
    "RAGCache": "lexigram.ai.rag.cache",
    # Tenancy
    "TenantScopedRAGPipeline": "lexigram.ai.rag.tenancy",
    # Strategy registries
    "RerankingStrategyRegistry": "lexigram.ai.rag.reranking.strategy_registry",
    "RetrievalStrategyRegistry": "lexigram.ai.rag.retrieval.strategy_registry",
    # Types
    "RerankResult": "lexigram.ai.rag.reranking.types",
    # Contracts re-exports
    "ChunkerProtocol": "lexigram.contracts.ai.vector",
}

if TYPE_CHECKING:
    from lexigram.ai.rag.cache import RAGCache
    from lexigram.ai.rag.chunking import (
        ChunkingConfig,
        create_chunker,
    )
    from lexigram.ai.rag.config import (
        IngestionConfig,
        PipelineConfig,
        RAGConfig,
        RAGTenancyConfig,
        RetrievalConfig,
        SynthesisConfig,
    )
    from lexigram.ai.rag.di.provider import RAGProvider
    from lexigram.ai.rag.events import (
        RetrievalCompletedEvent,
        SynthesisCompletedEvent,
    )
    from lexigram.ai.rag.hooks import (
        RAGAnswerSynthesizedHook,
        RAGDocumentsRetrievedHook,
        RAGPipelineStartedHook,
    )
    from lexigram.ai.rag.pipeline import RAGPipeline
    from lexigram.ai.rag.pipeline.builder import PipelineBuilder
    from lexigram.ai.rag.reranking.strategy_registry import (
        RerankingStrategyRegistry,
    )
    from lexigram.ai.rag.reranking.types import RerankResult
    from lexigram.ai.rag.retrieval.strategy_registry import (
        RetrievalStrategyRegistry,
    )
    from lexigram.ai.rag.tenancy import TenantScopedRAGPipeline
    from lexigram.ai.rag.types import (
        Chunk,
        Context,
        RAGError,
    )
    from lexigram.contracts.ai.vector import ChunkerProtocol


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        import importlib

        module = importlib.import_module(_LAZY_IMPORTS[name])
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__} has no attribute {name}")


def __dir__() -> list[str]:
    return __all__


__all__ = [
    "Chunk",
    "ChunkerProtocol",
    "ChunkingConfig",
    "Context",
    "IngestionConfig",
    "PipelineBuilder",
    "PipelineConfig",
    "RAGAnswerSynthesizedHook",
    "RAGCache",
    "RAGConfig",
    "RAGDocumentsRetrievedHook",
    "RAGError",
    "RAGModule",
    "RAGPipeline",
    "RAGPipelineStartedHook",
    "RAGProvider",
    "RAGTenancyConfig",
    "RerankResult",
    "RerankingStrategyRegistry",
    "RetrievalCompletedEvent",
    "RetrievalConfig",
    "RetrievalStrategyRegistry",
    "SynthesisCompletedEvent",
    "SynthesisConfig",
    "TenantScopedRAGPipeline",
    "create_chunker",
]
