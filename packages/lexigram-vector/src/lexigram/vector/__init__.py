"""Lexigram Vector — Vector store backends for the Lexigram Framework."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

try:
    __version__ = version("lexigram-vector")
except PackageNotFoundError:
    __version__ = "0.0.0"

if TYPE_CHECKING:
    from lexigram.vector.adapters.document_store import DocumentVectorStoreAdapter
    from lexigram.vector.adapters.vector_store import VectorStoreAdapter
    from lexigram.vector.backends.base import BaseVectorCollection, BaseVectorStore
    from lexigram.vector.backends.chroma import ChromaStore
    from lexigram.vector.backends.memory import MemoryVectorStore
    from lexigram.vector.backends.pgvector import PgVectorStore
    from lexigram.vector.backends.pinecone import PineconeStore
    from lexigram.vector.backends.qdrant import QdrantStore
    from lexigram.vector.config import (
        ChromaConfig,
        MemoryConfig,
        NamedVectorConfig,
        PgVectorConfig,
        PineconeConfig,
        QdrantConfig,
        VectorConfig,
    )
    from lexigram.vector.di.factories import create_vector_store
    from lexigram.vector.di.provider import VectorProvider
    from lexigram.vector.embedding.cache import EmbeddingCache, InMemoryEmbeddingCache
    from lexigram.vector.embedding.client import OpenAICompatibleEmbeddingClient
    from lexigram.vector.embedding.config import EmbeddingClientConfig
    from lexigram.vector.events import (
        VectorDeletedEvent,
        VectorIndexedEvent,
        VectorSearchedEvent,
    )
    from lexigram.vector.exceptions import (
        CollectionAlreadyExistsError,
        CollectionNotFoundError,
        DimensionMismatchError,
        FilterCompilationError,
        VectorConfigError,
        VectorConnectionError,
        VectorDeleteError,
        VectorError,
        VectorSearchError,
        VectorTimeoutError,
        VectorUpsertError,
    )
    from lexigram.vector.module import VectorModule
    from lexigram.vector.search.hybrid import (
        BM25Retriever,
        HybridRetriever,
        HybridSearchConfig,
        RRFReranker,
        create_hybrid_retriever,
    )
    from lexigram.vector.search.reranking import (
        CrossEncoderReranker,
        DiversityReranker,
        RerankerPipeline,
        RerankingConfig,
        RerankingStrategy,
        SimilarityReranker,
        create_reranker,
    )
    from lexigram.vector.testing.mocks import (
        MockVectorStore,
        MockVectorStoreWithErrors,
        MockVectorStoreWithSimilarity,
    )
    from lexigram.vector.types import Embedding

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "BaseVectorCollection": ("lexigram.vector.backends.base", "BaseVectorCollection"),
    "BaseVectorStore": ("lexigram.vector.backends.base", "BaseVectorStore"),
    "BM25Retriever": ("lexigram.vector.search.hybrid", "BM25Retriever"),
    "ChromaStore": ("lexigram.vector.backends.chroma", "ChromaStore"),
    "CollectionAlreadyExistsError": (
        "lexigram.vector.exceptions",
        "CollectionAlreadyExistsError",
    ),
    "CollectionNotFoundError": (
        "lexigram.vector.exceptions",
        "CollectionNotFoundError",
    ),
    "CrossEncoderReranker": (
        "lexigram.vector.search.reranking",
        "CrossEncoderReranker",
    ),
    "DimensionMismatchError": ("lexigram.vector.exceptions", "DimensionMismatchError"),
    "DiversityReranker": ("lexigram.vector.search.reranking", "DiversityReranker"),
    "DocumentVectorStoreAdapter": (
        "lexigram.vector.adapters.document_store",
        "DocumentVectorStoreAdapter",
    ),
    "Embedding": ("lexigram.vector.types", "Embedding"),
    "EmbeddingCache": ("lexigram.vector.embedding.cache", "EmbeddingCache"),
    "EmbeddingClientConfig": (
        "lexigram.vector.embedding.config",
        "EmbeddingClientConfig",
    ),
    "FilterCompilationError": ("lexigram.vector.exceptions", "FilterCompilationError"),
    "HybridRetriever": ("lexigram.vector.search.hybrid", "HybridRetriever"),
    "HybridSearchConfig": ("lexigram.vector.search.hybrid", "HybridSearchConfig"),
    "InMemoryEmbeddingCache": (
        "lexigram.vector.embedding.cache",
        "InMemoryEmbeddingCache",
    ),
    "MemoryConfig": ("lexigram.vector.config", "MemoryConfig"),
    "MemoryVectorStore": ("lexigram.vector.backends.memory", "MemoryVectorStore"),
    "MockVectorStore": ("lexigram.vector.testing.mocks", "MockVectorStore"),
    "MockVectorStoreWithErrors": (
        "lexigram.vector.testing.mocks",
        "MockVectorStoreWithErrors",
    ),
    "MockVectorStoreWithSimilarity": (
        "lexigram.vector.testing.mocks",
        "MockVectorStoreWithSimilarity",
    ),
    "NamedVectorConfig": ("lexigram.vector.config", "NamedVectorConfig"),
    "OpenAICompatibleEmbeddingClient": (
        "lexigram.vector.embedding.client",
        "OpenAICompatibleEmbeddingClient",
    ),
    "PgVectorConfig": ("lexigram.vector.config", "PgVectorConfig"),
    "PgVectorStore": ("lexigram.vector.backends.pgvector", "PgVectorStore"),
    "PineconeConfig": ("lexigram.vector.config", "PineconeConfig"),
    "PineconeStore": ("lexigram.vector.backends.pinecone", "PineconeStore"),
    "QdrantConfig": ("lexigram.vector.config", "QdrantConfig"),
    "QdrantStore": ("lexigram.vector.backends.qdrant", "QdrantStore"),
    "RRFReranker": ("lexigram.vector.search.hybrid", "RRFReranker"),
    "RerankingConfig": ("lexigram.vector.search.reranking", "RerankingConfig"),
    "RerankingStrategy": ("lexigram.vector.search.reranking", "RerankingStrategy"),
    "RerankerPipeline": ("lexigram.vector.search.reranking", "RerankerPipeline"),
    "SimilarityReranker": ("lexigram.vector.search.reranking", "SimilarityReranker"),
    "VectorConfig": ("lexigram.vector.config", "VectorConfig"),
    "VectorConfigError": ("lexigram.vector.exceptions", "VectorConfigError"),
    "VectorConnectionError": ("lexigram.vector.exceptions", "VectorConnectionError"),
    "VectorDeletedEvent": ("lexigram.vector.events", "VectorDeletedEvent"),
    "VectorDeleteError": ("lexigram.vector.exceptions", "VectorDeleteError"),
    "VectorError": ("lexigram.vector.exceptions", "VectorError"),
    "VectorIndexedEvent": ("lexigram.vector.events", "VectorIndexedEvent"),
    "VectorModule": ("lexigram.vector.module", "VectorModule"),
    "VectorProvider": ("lexigram.vector.di.provider", "VectorProvider"),
    "VectorSearchedEvent": ("lexigram.vector.events", "VectorSearchedEvent"),
    "VectorSearchError": ("lexigram.vector.exceptions", "VectorSearchError"),
    "VectorStoreAdapter": (
        "lexigram.vector.adapters.vector_store",
        "VectorStoreAdapter",
    ),
    "VectorTenancyConfig": ("lexigram.vector.config", "VectorTenancyConfig"),
    "VectorTimeoutError": ("lexigram.vector.exceptions", "VectorTimeoutError"),
    "VectorUpsertError": ("lexigram.vector.exceptions", "VectorUpsertError"),
    # Tenancy
    "TemplatedTenantCollectionResolver": (
        "lexigram.vector.tenancy.resolver",
        "TemplatedTenantCollectionResolver",
    ),
    "PineconeNamespaceTenantResolver": (
        "lexigram.vector.tenancy.pinecone_namespace",
        "PineconeNamespaceTenantResolver",
    ),
    "TenantVectorStoreDecorator": (
        "lexigram.vector.tenancy.decorator",
        "TenantVectorStoreDecorator",
    ),
    "create_hybrid_retriever": (
        "lexigram.vector.search.hybrid",
        "create_hybrid_retriever",
    ),
    "create_reranker": ("lexigram.vector.search.reranking", "create_reranker"),
    "create_vector_store": ("lexigram.vector.di.factories", "create_vector_store"),
    # Hooks
    "VectorIndexedHook": ("lexigram.vector.hooks", "VectorIndexedHook"),
    "VectorSearchedHook": ("lexigram.vector.hooks", "VectorSearchedHook"),
}


def __getattr__(name: str) -> Any:
    """Lazy-load symbols on first access."""
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Enumerate available attributes for IDE support."""
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = [
    "BM25Retriever",
    "BaseVectorCollection",
    "BaseVectorStore",
    "ChromaStore",
    "CollectionAlreadyExistsError",
    "CollectionNotFoundError",
    "CrossEncoderReranker",
    "DimensionMismatchError",
    "DiversityReranker",
    "DocumentVectorStoreAdapter",
    "Embedding",
    "EmbeddingCache",
    "EmbeddingClientConfig",
    "FilterCompilationError",
    "HybridRetriever",
    "HybridSearchConfig",
    "InMemoryEmbeddingCache",
    "MemoryConfig",
    "MemoryVectorStore",
    "MockVectorStore",
    "MockVectorStoreWithErrors",
    "MockVectorStoreWithSimilarity",
    "NamedVectorConfig",
    "OpenAICompatibleEmbeddingClient",
    "PgVectorConfig",
    "PgVectorStore",
    "PineconeConfig",
    "PineconeNamespaceTenantResolver",
    "PineconeStore",
    "QdrantConfig",
    "QdrantStore",
    "RRFReranker",
    "RerankerPipeline",
    "RerankingConfig",
    "RerankingStrategy",
    "SimilarityReranker",
    "TemplatedTenantCollectionResolver",
    "TenantVectorStoreDecorator",
    "VectorConfig",
    "VectorConfigError",
    "VectorConnectionError",
    "VectorDeleteError",
    "VectorDeletedEvent",
    "VectorError",
    "VectorIndexedEvent",
    "VectorIndexedHook",
    "VectorModule",
    "VectorProvider",
    "VectorSearchError",
    "VectorSearchedEvent",
    "VectorSearchedHook",
    "VectorStoreAdapter",
    "VectorTenancyConfig",
    "VectorTimeoutError",
    "VectorUpsertError",
    "create_hybrid_retriever",
    "create_reranker",
    "create_vector_store",
]
