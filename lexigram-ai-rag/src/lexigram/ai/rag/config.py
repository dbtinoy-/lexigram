from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, ClassVar, cast

from lexigram.ai.rag.constants import ENV_NESTED_DELIMITER, ENV_PREFIX
from lexigram.ai.rag.synthesis.types import SynthesisConfig
from lexigram.config.base import BaseConfig
from lexigram.domain.models import DomainModel
from lexigram.validation import ConfigDict, Field


@dataclass(init=False)
class RAGTenancyConfig(DomainModel):
    """Optional tenant-aware RAG pipeline configuration.

    When enabled, the RAG provider wraps the ``RAGPipelineProtocol`` binding
    in a ``TenantScopedRAGPipeline`` that resolves the ``collection_name``
    from the current tenant context at request time, with per-tenant
    pipeline instance caching.

    Note:
        Requires ``lexigram-tenancy`` in the module graph when ``enabled``
        is ``True`` — the provider resolves ``Context`` at boot.
    """

    enabled: bool = Field(
        default=False,
        description="Enable tenant-aware collection resolution in RAG pipeline",
    )


class RAGConfig(BaseConfig):
    """Configuration for RAG (Retrieval Augmented Generation) pipeline.

    Example:
        >>> config = RAGConfig(
        ...     vector_store_type="chroma",
        ...     collection_name="pet_knowledge",
        ...     top_k=5,
        ...     enable_citations=True
        ...     )
    """

    config_section: ClassVar[str] = "ai_rag"

    def with_collection(self, name: str) -> RAGConfig:
        """Return a copy of this config with a different *collection_name*.

        Usage::

            tenant_config = base_config.with_collection("canon_t_tenant42")
        """
        return self.model_copy(update={"collection_name": name})

    model_config: ClassVar[ConfigDict] = cast(
        "ConfigDict",
        {
            "env_prefix": ENV_PREFIX,
            "env_nested_delimiter": ENV_NESTED_DELIMITER,
            "extra": "ignore",
        },
    )

    # Feature toggle
    enabled: bool = Field(
        default=True,
        description="Enable the RAG pipeline",
    )

    # Local persistence (for Chroma and similar file-based stores)
    persist_directory: str | None = Field(
        default=None,
        description="Local directory path for vector store persistence (e.g. Chroma)",
    )

    # Vector Store
    vector_store_type: str = Field(
        default="pgvector",
        description="Vector store backend (pgvector, chroma, qdrant, mock)",
    )
    vector_dimension: int = Field(
        default=1536,
        ge=1,
        description="Embedding vector dimension (1536 for OpenAI ada-002)",
    )
    collection_name: str = Field(
        default="default",
        description="Collection/index name for vector store",
    )

    # Retrieval
    top_k: int = Field(
        default=5,
        ge=1,
        description="Number of documents to retrieve",
    )
    similarity_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score threshold",
    )
    use_hybrid_search: bool = Field(
        default=True,
        description="Enable hybrid search (semantic + keyword)",
    )

    # Embedding Model
    embedding_provider: str = Field(
        default="openai",
        description="Embedding provider (openai, cohere, etc.)",
    )
    embedding_model: str | None = Field(
        default=None,
        description="Embedding model identifier. Must be set explicitly — no vendor-specific default.",
    )

    # Citations
    enable_citations: bool = Field(
        default=True,
        description="Include source citations in responses",
    )
    citation_style: str = Field(
        default="inline",
        description="Citation style (inline, footnote, numbered)",
    )
    min_citation_confidence: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for citation inclusion",
    )

    # Chunking
    chunk_size: int = Field(
        default=512,
        ge=1,
        description="Text chunk size in tokens",
    )
    chunk_overlap: int = Field(
        default=50,
        ge=0,
        description="Overlap between consecutive chunks",
    )
    chunking_strategy: str = Field(
        default="recursive",
        description="Chunking strategy (recursive, semantic, token)",
    )

    # Query Enhancement
    enable_query_expansion: bool = Field(
        default=True,
        description="Enable query expansion techniques",
    )
    enable_hyde: bool = Field(
        default=False,
        description="Enable HyDE (Hypothetical Document Embeddings)",
    )

    # Response Synthesis
    synthesis_strategy: str = Field(
        default="hybrid",
        description="Synthesis strategy (direct, extractive, abstractive, hybrid)",
    )
    enable_hallucination_detection: bool = Field(
        default=True,
        description="Enable hallucination detection for AI responses",
    )

    # Cache
    enable_caching: bool = Field(
        default=True,
        description="Enable caching for RAG queries",
    )
    cache_ttl: int = Field(
        default=3600,
        ge=0,
        description="Cache TTL in seconds (default: 1 hour)",
    )

    # Tenancy
    tenancy: RAGTenancyConfig = Field(
        default_factory=RAGTenancyConfig,
        description="Optional tenant-aware RAG pipeline configuration",
    )


class PipelineStageType(StrEnum):
    """Types of stages in a RAG pipeline."""

    INGESTION = "ingestion"
    QUERY_PROCESSING = "query_processing"
    RETRIEVAL = "retrieval"
    CONTEXT_OPTIMIZATION = "context_optimization"
    SYNTHESIS = "synthesis"
    QUALITY_ASSURANCE = "quality_assurance"
    POST_PROCESSING = "post_processing"


class DocumentFormat(StrEnum):
    """Supported document formats for ingestion."""

    TEXT = "text"
    PDF = "pdf"
    MARKDOWN = "markdown"
    HTML = "html"


class RoutingStrategyType(StrEnum):
    """Routing strategy types."""

    RULE_BASED = "rule_based"
    SEMANTIC = "semantic"
    LLM = "llm"
    HYBRID = "hybrid"


class IngestionConfig(BaseConfig):
    """Configuration for document ingestion stage."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = Field(default=True)
    document_formats: list[DocumentFormat] = Field(
        default_factory=lambda: [
            DocumentFormat.TEXT,
            DocumentFormat.PDF,
            DocumentFormat.MARKDOWN,
        ],
    )
    preprocessing_enabled: bool = Field(default=False)
    ocr_enabled: bool = Field(default=False)
    table_extraction_enabled: bool = Field(default=False)
    metadata_enrichment_enabled: bool = Field(default=False)
    chunking_strategy: str = Field(default="recursive")
    chunk_size: int = Field(default=1000)
    chunk_overlap: int = Field(default=200)
    min_chunk_size: int = Field(default=100)
    error_strategy: str = Field(default="graceful")
    fail_fast: bool = Field(default=False)


class QueryProcessingConfig(BaseConfig):
    """Configuration for query processing stage."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = Field(default=True)
    transformation_enabled: bool = Field(default=False)
    transformation_strategies: list[str] = Field(default_factory=lambda: ["expansion"])
    hyde_enabled: bool = Field(default=False)
    hyde_num_documents: int = Field(default=1)
    routing_enabled: bool = Field(default=False)
    routing_strategy: RoutingStrategyType = Field(
        default=RoutingStrategyType.RULE_BASED
    )
    error_strategy: str = Field(default="graceful")


class RetrievalConfig(BaseConfig):
    """Configuration for retrieval stage."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = Field(default=True)
    strategy: str = Field(default="hybrid")
    vector_search_enabled: bool = Field(default=True)
    top_k: int = Field(default=10)
    similarity_threshold: float = Field(default=0.0)
    knowledge_graph_enabled: bool = Field(default=False)
    max_graph_depth: int = Field(default=2)
    multi_hop_enabled: bool = Field(default=False)
    max_hops: int = Field(default=3)
    error_strategy: str = Field(default="fail_fast")


class ContextOptimizationConfig(BaseConfig):
    """Configuration for context optimization stage."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = Field(default=True)
    strategy: str = Field(default="cross-encoder")
    top_k: int = Field(default=5)
    ranking_enabled: bool = Field(default=True)
    compression_enabled: bool = Field(default=False)
    compression_strategy: str = Field(default="hybrid")
    max_context_tokens: int = Field(default=4000)
    deduplication_enabled: bool = Field(default=True)
    deduplication_threshold: float = Field(default=0.9)
    citations_enabled: bool = Field(default=True)
    error_strategy: str = Field(default="graceful")


class QualityAssuranceConfig(BaseConfig):
    """Configuration for quality assurance stage."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = Field(default=True)
    min_faithfulness: float = Field(default=0.7)
    min_relevance: float = Field(default=0.6)
    min_confidence: float = Field(default=0.5)
    hallucination_detection_enabled: bool = Field(default=True)
    hallucination_strict_mode: bool = Field(default=False)
    reject_low_quality: bool = Field(default=False)
    warn_low_quality: bool = Field(default=True)
    error_strategy: str = Field(default="graceful")


class PostProcessingConfig(BaseConfig):
    """Configuration for post-processing stage."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = Field(default=True)
    cache_enabled: bool = Field(default=True)
    cache_results: bool = Field(default=True)
    collect_metrics: bool = Field(default=True)
    detailed_logging: bool = Field(default=False)
    error_strategy: str = Field(default="skip")


class PipelineConfig(BaseConfig):
    """Complete pipeline configuration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    name: str = Field(default="default-rag-pipeline")
    description: str = Field(default="")
    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)
    query_processing: QueryProcessingConfig = Field(
        default_factory=QueryProcessingConfig
    )
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    context_optimization: ContextOptimizationConfig = Field(
        default_factory=ContextOptimizationConfig
    )
    synthesis: SynthesisConfig = Field(default_factory=SynthesisConfig)
    quality_assurance: QualityAssuranceConfig = Field(
        default_factory=QualityAssuranceConfig
    )
    post_processing: PostProcessingConfig = Field(default_factory=PostProcessingConfig)

    stages: list[PipelineStageType] = Field(
        default_factory=lambda: [
            PipelineStageType.RETRIEVAL,
            PipelineStageType.SYNTHESIS,
            PipelineStageType.QUALITY_ASSURANCE,
        ],
        description="Ordered list of pipeline stages to execute",
    )

    max_retries: int = Field(default=3)
    retry_delay: float = Field(default=1.0)
    default_error_strategy: str = Field(default="graceful")
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Auto-evaluation hook (P7.1)
    auto_evaluate_every_n: int | None = Field(
        default=None,
        description="Run automatic evaluation every N pipeline requests. None disables auto-evaluation.",
    )

    # Citation enforcement (P7.2)
    require_citations: bool = Field(
        default=False,
        description="Raise MissingCitationsError when the synthesis result contains no citations.",
    )

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> PipelineConfig:
        """Create configuration from dictionary."""
        return cls(**config_dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "default_error_strategy": self.default_error_strategy,
            "metadata": self.metadata,
        }


@dataclass(init=False)
class RAGTenancyConfig(DomainModel):
    """Optional tenant-aware RAG pipeline configuration.

    When enabled, the RAG provider wraps the ``RAGPipelineProtocol`` binding
    in a ``TenantScopedRAGPipeline`` that resolves the ``collection_name``
    from the current tenant context at request time, with per-tenant
    pipeline instance caching.

    Note:
        Requires ``lexigram-tenancy`` in the module graph when ``enabled``
        is ``True`` — the provider resolves ``Context`` at boot.
    """

    enabled: bool = Field(
        default=False,
        description="Enable tenant-aware collection resolution in RAG pipeline",
    )


__all__ = [
    "ContextOptimizationConfig",
    "DocumentFormat",
    "IngestionConfig",
    "PipelineConfig",
    "PipelineStageType",
    "PostProcessingConfig",
    "QualityAssuranceConfig",
    "QueryProcessingConfig",
    "RAGConfig",
    "RAGTenancyConfig",
    "RetrievalConfig",
    "RoutingStrategyType",
    "SynthesisConfig",
]
