from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from lexigram.domain import DomainModel
from lexigram.validation import Field


class CacheType(StrEnum):
    """Types of caches in RAG system."""

    EMBEDDING = "embedding"
    RETRIEVAL = "retrieval"
    DOCUMENT = "document"
    RERANKING = "reranking"
    LLM_RESPONSE = "llm_response"
    QUERY_TRANSFORMATION = "query_transformation"


@dataclass(init=False)
class RAGCacheConfig(DomainModel):
    """Configuration for RAG caching system."""

    embedding_ttl: int = Field(
        default=86400,  # 24 hours
        description="TTL for embedding cache in seconds",
    )
    retrieval_ttl: int = Field(
        default=300,  # 5 minutes
        description="TTL for retrieval cache in seconds",
    )
    document_ttl: int = Field(
        default=3600,  # 1 hour
        description="TTL for document cache in seconds",
    )
    reranking_ttl: int = Field(
        default=600,  # 10 minutes
        description="TTL for reranking cache in seconds",
    )
    llm_response_ttl: int = Field(
        default=1800,  # 30 minutes
        description="TTL for LLM responses in seconds",
    )
    query_transformation_ttl: int = Field(
        default=3600,  # 1 hour
        description="TTL for query transformations in seconds",
    )
    key_prefix: str = Field(
        default="rag:",
        description="Prefix for all cache keys",
    )
    enable_stats: bool = Field(
        default=True,
        description="Enable cache statistics tracking",
    )
    max_embedding_cache_size: int = Field(
        default=10000,
        description="Maximum number of embeddings to cache",
    )
    max_retrieval_cache_size: int = Field(
        default=1000,
        description="Maximum number of retrieval results to cache",
    )
