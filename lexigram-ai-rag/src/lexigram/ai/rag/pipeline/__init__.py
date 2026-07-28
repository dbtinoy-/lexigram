"""RAG pipeline implementation.

This module provides a complete, production-ready RAG pipeline that
integrates all components from document ingestion through response
synthesis and quality assurance.
"""

from __future__ import annotations

from lexigram.ai.rag.config import (
    ContextOptimizationConfig,
    DocumentFormat,
    IngestionConfig,
    PipelineConfig,
    PostProcessingConfig,
    QualityAssuranceConfig,
    QueryProcessingConfig,
    RetrievalConfig,
    SynthesisConfig,
)
from lexigram.ai.rag.pipeline.base import PipelineStageProtocol
from lexigram.ai.rag.pipeline.builder import PipelineBuilder, RAGPipeline
from lexigram.ai.rag.pipeline.executor import PipelineExecutor
from lexigram.ai.rag.pipeline.types import (
    ErrorStrategy,
    PipelineContext,
    PipelineError,
    StageMetrics,
    StageStatus,
)

__all__ = [
    "ContextOptimizationConfig",
    "DocumentFormat",
    "ErrorStrategy",
    "IngestionConfig",
    "PipelineBuilder",
    # Configuration
    "PipelineConfig",
    # Context and errors
    "PipelineContext",
    "PipelineError",
    "PipelineExecutor",
    "PipelineStageProtocol",
    "PostProcessingConfig",
    "QualityAssuranceConfig",
    "QueryProcessingConfig",
    # Core pipeline
    "RAGPipeline",
    "RetrievalConfig",
    "StageMetrics",
    "StageStatus",
    "SynthesisConfig",
]
