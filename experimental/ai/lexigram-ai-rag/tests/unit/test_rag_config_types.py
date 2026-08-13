"""Tests for RAG config types."""

import pytest

from lexigram.ai.rag.config import (
    DocumentFormat,
    PipelineStageType,
    RoutingStrategyType,
)


class TestPipelineStageType:
    """Tests for PipelineStageType enum."""

    def test_pipeline_stage_type_values(self) -> None:
        """Test PipelineStageType enum values."""
        assert PipelineStageType.INGESTION.value == "ingestion"
        assert PipelineStageType.QUERY_PROCESSING.value == "query_processing"
        assert PipelineStageType.RETRIEVAL.value == "retrieval"
        assert PipelineStageType.CONTEXT_OPTIMIZATION.value == "context_optimization"
        assert PipelineStageType.SYNTHESIS.value == "synthesis"
        assert PipelineStageType.QUALITY_ASSURANCE.value == "quality_assurance"

    def test_pipeline_stage_type_members(self) -> None:
        """Test PipelineStageType has expected members."""
        members = list(PipelineStageType)
        assert len(members) >= 6


class TestDocumentFormat:
    """Tests for DocumentFormat enum."""

    def test_document_format_values(self) -> None:
        """Test DocumentFormat enum values."""
        assert DocumentFormat.TEXT.value == "text"
        assert DocumentFormat.PDF.value == "pdf"
        assert DocumentFormat.MARKDOWN.value == "markdown"
        assert DocumentFormat.HTML.value == "html"

    def test_document_format_members(self) -> None:
        """Test DocumentFormat has expected members."""
        members = list(DocumentFormat)
        assert len(members) == 4


class TestRoutingStrategyType:
    """Tests for RoutingStrategyType enum."""

    def test_routing_strategy_type_values(self) -> None:
        """Test RoutingStrategyType enum values."""
        assert RoutingStrategyType.RULE_BASED.value == "rule_based"
        assert RoutingStrategyType.SEMANTIC.value == "semantic"
        assert RoutingStrategyType.LLM.value == "llm"
        assert RoutingStrategyType.HYBRID.value == "hybrid"

    def test_routing_strategy_type_members(self) -> None:
        """Test RoutingStrategyType has expected members."""
        members = list(RoutingStrategyType)
        assert len(members) == 4
