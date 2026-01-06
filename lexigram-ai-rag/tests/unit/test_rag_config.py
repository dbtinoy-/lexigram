"""Unit tests for lexigram.ai.rag.config module."""

from __future__ import annotations

from lexigram.ai.rag.config import (
    ContextOptimizationConfig,
    DocumentFormat,
    IngestionConfig,
    PipelineConfig,
    PipelineStageType,
    PostProcessingConfig,
    QualityAssuranceConfig,
    QueryProcessingConfig,
    RAGConfig,
    RAGTenancyConfig,
    RetrievalConfig,
    RoutingStrategyType,
    SynthesisConfig,
)


# ── StrEnum types ────────────────────────────────────────────────────

class TestEnums:
    def test_pipeline_stage_type_values(self) -> None:
        assert PipelineStageType.INGESTION == "ingestion"
        assert PipelineStageType.RETRIEVAL == "retrieval"
        assert PipelineStageType.SYNTHESIS == "synthesis"

    def test_document_format_values(self) -> None:
        assert DocumentFormat.PDF == "pdf"
        assert DocumentFormat.MARKDOWN == "markdown"
        assert DocumentFormat.HTML == "html"

    def test_routing_strategy_type_values(self) -> None:
        assert RoutingStrategyType.RULE_BASED == "rule_based"
        assert RoutingStrategyType.SEMANTIC == "semantic"
        assert RoutingStrategyType.LLM == "llm"
        assert RoutingStrategyType.HYBRID == "hybrid"


# ── RAGConfig ────────────────────────────────────────────────────────

class TestRAGConfig:
    def test_defaults(self) -> None:
        cfg = RAGConfig()
        assert cfg.enabled is True
        assert cfg.vector_store_type == "pgvector"
        assert cfg.vector_dimension == 1536
        assert cfg.top_k == 5
        assert cfg.similarity_threshold == 0.7
        assert cfg.use_hybrid_search is True
        assert cfg.embedding_provider == "openai"
        assert cfg.enable_citations is True
        assert cfg.chunk_size == 512
        assert cfg.chunk_overlap == 50
        assert cfg.chunking_strategy == "recursive"
        assert cfg.synthesis_strategy == "hybrid"
        assert cfg.enable_caching is True
        assert cfg.cache_ttl == 3600

    def test_custom_values(self) -> None:
        cfg = RAGConfig(
            vector_store_type="qdrant",
            top_k=10,
            enable_hyde=True,
        )
        assert cfg.vector_store_type == "qdrant"
        assert cfg.top_k == 10
        assert cfg.enable_hyde is True


# ── Stage configs ────────────────────────────────────────────────────

class TestIngestionConfig:
    def test_defaults(self) -> None:
        cfg = IngestionConfig()
        assert cfg.enabled is True
        assert DocumentFormat.TEXT in cfg.document_formats
        assert cfg.chunk_size == 1000
        assert cfg.chunk_overlap == 200

    def test_custom(self) -> None:
        cfg = IngestionConfig(chunk_size=500, ocr_enabled=True)
        assert cfg.chunk_size == 500
        assert cfg.ocr_enabled is True


class TestQueryProcessingConfig:
    def test_defaults(self) -> None:
        cfg = QueryProcessingConfig()
        assert cfg.enabled is True
        assert cfg.hyde_enabled is False
        assert cfg.routing_strategy == RoutingStrategyType.RULE_BASED


class TestRetrievalConfig:
    def test_defaults(self) -> None:
        cfg = RetrievalConfig()
        assert cfg.top_k == 10
        assert cfg.similarity_threshold == 0.0
        assert cfg.knowledge_graph_enabled is False


class TestContextOptimizationConfig:
    def test_defaults(self) -> None:
        cfg = ContextOptimizationConfig()
        assert cfg.ranking_enabled is True
        assert cfg.compression_enabled is False
        assert cfg.max_context_tokens == 4000
        assert cfg.deduplication_threshold == 0.9


class TestSynthesisConfig:
    def test_defaults(self) -> None:
        cfg = SynthesisConfig()
        assert cfg.strategy == "hybrid"
        assert cfg.include_citations is True
        assert cfg.output_format == "markdown"


class TestQualityAssuranceConfig:
    def test_defaults(self) -> None:
        cfg = QualityAssuranceConfig()
        assert cfg.min_faithfulness == 0.7
        assert cfg.hallucination_detection_enabled is True
        assert cfg.reject_low_quality is False


class TestPostProcessingConfig:
    def test_defaults(self) -> None:
        cfg = PostProcessingConfig()
        assert cfg.cache_enabled is True
        assert cfg.collect_metrics is True


# ── PipelineConfig ───────────────────────────────────────────────────

class TestPipelineConfig:
    def test_defaults(self) -> None:
        cfg = PipelineConfig()
        assert cfg.name == "default-rag-pipeline"
        assert cfg.max_retries == 3
        assert cfg.retry_delay == 1.0
        assert PipelineStageType.RETRIEVAL in cfg.stages
        assert PipelineStageType.SYNTHESIS in cfg.stages

    def test_from_dict(self) -> None:
        cfg = PipelineConfig.from_dict({"name": "custom", "max_retries": 5})
        assert cfg.name == "custom"
        assert cfg.max_retries == 5

    def test_to_dict(self) -> None:
        cfg = PipelineConfig(name="test")
        d = cfg.to_dict()
        assert d["name"] == "test"
        assert "max_retries" in d
        assert "metadata" in d

    def test_auto_evaluate_and_require_citations(self) -> None:
        cfg = PipelineConfig(
            auto_evaluate_every_n=10,
            require_citations=True,
        )
        assert cfg.auto_evaluate_every_n == 10
        assert cfg.require_citations is True


# ── RAGTenancyConfig ──────────────────────────────────────────────────

class TestRAGTenancyConfig:
    def test_defaults_disabled(self) -> None:
        cfg = RAGTenancyConfig()
        assert cfg.enabled is False

    def test_enabled(self) -> None:
        cfg = RAGTenancyConfig(enabled=True)
        assert cfg.enabled is True

    def test_on_rag_config_defaults(self) -> None:
        cfg = RAGConfig()
        assert cfg.tenancy.enabled is False

    def test_on_rag_config_with_tenancy(self) -> None:
        cfg = RAGConfig(tenancy=RAGTenancyConfig(enabled=True))
        assert cfg.tenancy.enabled is True

    def test_with_collection_creates_copy(self) -> None:
        cfg = RAGConfig(collection_name="default")
        tenant_cfg = cfg.with_collection("tenant_collection")
        assert tenant_cfg.collection_name == "tenant_collection"
        assert cfg.collection_name == "default"  # original unchanged
