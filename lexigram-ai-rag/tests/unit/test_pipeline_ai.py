"""Tests for RAG pipeline integration.

This module contains tests for the complete RAG pipeline,
including unit tests, integration tests, and end-to-end tests.
"""

import pytest

from lexigram.ai.rag.chunking import Chunk
from lexigram.ai.rag.pipeline import (
    ErrorStrategy,
    PipelineBuilder,
    PipelineContext,
    StageStatus,
)
from lexigram.ai.rag.synthesis import (
    ContextChunk,
    SynthesisResult,
    SynthesisStrategy,
)

# ============================================================================
# Unit Tests - PipelineContext
# ============================================================================


class TestPipelineContext:
    """Tests for PipelineContext."""

    def test_context_creation(self):
        """Test creating a pipeline context."""
        context = PipelineContext(query="What is Python?")

        assert context.query == "What is Python?"
        assert context.documents == []
        assert context.chunks == []
        assert context.has_errors is False
        assert context.has_warnings is False
        assert len(context.request_id) > 0

    def test_add_error(self):
        """Test adding errors to context."""
        context = PipelineContext(query="test")

        error = ValueError("test error")
        context.add_error("test_stage", error, recoverable=True)

        assert context.has_errors is True
        assert len(context.errors) == 1
        assert context.errors[0].stage == "test_stage"
        assert context.errors[0].recoverable is True

    def test_add_warning(self):
        """Test adding warnings to context."""
        context = PipelineContext(query="test")

        context.add_warning("test warning")

        assert context.has_warnings is True
        assert len(context.warnings) == 1
        assert context.warnings[0] == "test warning"

    def test_stage_timing(self):
        """Test stage timing tracking."""
        context = PipelineContext(query="test")

        context.start_stage("test_stage")
        assert len(context.stage_metrics) == 1
        assert context.stage_metrics[0].status == StageStatus.RUNNING

        context.complete_stage("test_stage", StageStatus.COMPLETED)
        assert context.stage_metrics[0].status == StageStatus.COMPLETED
        assert context.stage_metrics[0].duration_ms >= 0

    def test_token_usage_tracking(self):
        """Test token usage tracking."""
        context = PipelineContext(query="test")

        context.record_token_usage("embedding", 100)
        context.record_token_usage("llm_call", 500)
        context.record_token_usage("embedding", 50)

        assert context.token_usage["embedding"] == 150
        assert context.token_usage["llm_call"] == 500

    def test_cache_hit_tracking(self):
        """Test cache hit tracking."""
        context = PipelineContext(query="test")

        context.record_cache_hit("query_cache", True)
        context.record_cache_hit("embedding_cache", False)

        assert context.cache_hits["query_cache"] is True
        assert context.cache_hits["embedding_cache"] is False

    def test_failed_stages(self):
        """Test getting failed stages."""
        context = PipelineContext(query="test")

        context.start_stage("stage1")
        context.complete_stage("stage1", StageStatus.COMPLETED)

        context.start_stage("stage2")
        context.complete_stage("stage2", StageStatus.FAILED)

        assert len(context.failed_stages) == 1
        assert "stage2" in context.failed_stages
        assert len(context.completed_stages) == 1
        assert "stage1" in context.completed_stages

    def test_to_dict(self):
        """Test converting context to dictionary."""
        context = PipelineContext(query="What is Python?")
        context.record_token_usage("embedding", 100)
        context.add_warning("test warning")

        result = context.to_dict()

        assert result["query"] == "What is Python?"
        assert result["error_count"] == 0
        assert result["warning_count"] == 1
        assert result["token_usage"]["embedding"] == 100


# ============================================================================
# Unit Tests - Pipeline Configuration
# ============================================================================


class TestPipelineConfiguration:
    """Tests for pipeline configuration."""

    def test_default_config(self):
        """Test default pipeline configuration."""
        builder = PipelineBuilder()

        assert builder.config.name == "default-rag-pipeline"
        assert builder.config.synthesis.enabled is True
        assert builder.config.retrieval.enabled is True

    def test_fluent_api(self):
        """Test fluent configuration API."""
        builder = (
            PipelineBuilder()
            .with_name("test-pipeline")
            .with_retrieval(top_k=5)
            .with_synthesis(strategy=SynthesisStrategy.DIRECT)
            .with_quality_assurance(min_confidence=0.8)
        )

        assert builder.config.name == "test-pipeline"
        assert builder.config.retrieval.top_k == 5
        assert builder.config.synthesis.strategy == SynthesisStrategy.DIRECT
        assert builder.config.quality_assurance.min_confidence == 0.8

    def test_error_strategy_config(self):
        """Test error strategy configuration."""
        builder = PipelineBuilder().with_error_strategy(
            ErrorStrategy.RETRY,
            max_retries=5,
            retry_delay=2.0,
        )

        assert builder.config.default_error_strategy == ErrorStrategy.RETRY
        assert builder.config.max_retries == 5
        assert builder.config.retry_delay == 2.0

    def test_from_dict(self):
        """Test creating config from dictionary."""
        config_dict = {
            "name": "dict-pipeline",
            "retrieval": {"top_k": 15},
            "synthesis": {"strategy": "extractive"},
        }

        builder = PipelineBuilder().from_dict(config_dict)

        assert builder.config.name == "dict-pipeline"
        assert builder.config.retrieval.top_k == 15


# ============================================================================
# Integration Tests - Pipeline Execution
# ============================================================================


class TestPipelineIntegration:
    """Integration tests for complete pipeline execution."""

    @pytest.mark.asyncio
    async def test_simple_pipeline_execution(self):
        """Test simple pipeline execution with mock data."""
        # Create pipeline with minimal config
        pipeline = (
            PipelineBuilder()
            .with_name("test-pipeline")
            .with_retrieval(top_k=3)
            .with_synthesis(strategy=SynthesisStrategy.DIRECT)
            .with_quality_assurance(enabled=False)  # Disable for simple test
            .build()
        )

        # Create test chunks
        chunks = [
            Chunk(
                text="Python is a high-level programming language.",
                start_index=0,
                end_index=45,
                chunk_index=0,
                metadata={"source": "doc1.txt"},
            ),
            Chunk(
                text="Python is known for its readability.",
                start_index=0,
                end_index=37,
                chunk_index=1,
                metadata={"source": "doc2.txt"},
            ),
            Chunk(
                text="Python supports multiple programming paradigms.",
                start_index=0,
                end_index=48,
                chunk_index=2,
                metadata={"source": "doc3.txt"},
            ),
        ]

        # Execute pipeline
        context = await pipeline.run(
            query="What is Python?",
            documents=[],
        )

        # Manually set chunks for testing (since we don't have ingestion stage yet)
        context.chunks = chunks

        # Run through stages manually for testing
        from lexigram.ai.rag.pipeline.stages import (
            RetrievalStage,
            SynthesisStage,
        )

        retrieval_stage = RetrievalStage(config=pipeline.config.retrieval)
        context = await retrieval_stage.process(context)

        synthesis_stage = SynthesisStage(config=pipeline.config.synthesis)
        context = await synthesis_stage.process(context)

        # Verify results
        assert context.has_errors is False
        assert context.retrieved_chunks is not None
        assert len(context.retrieved_chunks) > 0
        assert context.synthesis_result is not None
        assert len(context.synthesis_result.response) > 0

    @pytest.mark.asyncio
    async def test_pipeline_with_quality_check(self):
        """Test pipeline with quality assurance enabled."""
        pipeline = (
            PipelineBuilder()
            .with_synthesis(strategy=SynthesisStrategy.DIRECT)
            .with_quality_assurance(
                enabled=True,
                min_confidence=0.3,  # Low threshold for test
                reject_low_quality=False,
            )
            .build()
        )

        # Create test context with synthesis result
        context = PipelineContext(query="What is Python?")

        # Create mock synthesis result
        chunks = [
            ContextChunk(
                text="Python is a programming language",
                source="doc1.txt",
                score=0.9,
                metadata={},
            ),
        ]

        context.synthesis_result = SynthesisResult(
            query="What is Python?",
            response="Python is a programming language.",
            strategy=SynthesisStrategy.DIRECT,
            context_chunks=chunks,
            quality_metrics=None,
            sources=["doc1.txt"],
            citations=[],
            metadata={},
        )

        # Run quality assurance
        from lexigram.ai.rag.pipeline.stages import QualityAssuranceStage

        qa_stage = QualityAssuranceStage(config=pipeline.config.quality_assurance)
        context = await qa_stage.process(context)

        # Verify quality metrics were calculated
        assert context.quality_metrics is not None
        assert context.quality_metrics.confidence >= 0
        assert context.quality_metrics.faithfulness >= 0

    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self):
        """Test pipeline error handling."""
        pipeline = (
            PipelineBuilder()
            .with_synthesis(strategy=SynthesisStrategy.DIRECT)
            .with_error_strategy(ErrorStrategy.GRACEFUL)
            .build()
        )

        # Create context that will cause errors
        context = PipelineContext(query="test")
        # No chunks - should cause synthesis to fail gracefully

        from lexigram.ai.rag.pipeline.stages import SynthesisStage

        synthesis_stage = SynthesisStage(config=pipeline.config.synthesis)
        result_context = await synthesis_stage.process(context)

        # Should have warnings but not fail
        assert result_context.has_warnings is True


# ============================================================================
# Performance Tests
# ============================================================================


class TestPipelinePerformance:
    """Performance tests for pipeline execution."""

    @pytest.mark.asyncio
    async def test_pipeline_latency(self):
        """Test pipeline execution latency."""
        import time

        pipeline = (
            PipelineBuilder()
            .with_synthesis(strategy=SynthesisStrategy.DIRECT)
            .with_quality_assurance(enabled=False)
            .build()
        )

        start_time = time.time()

        context = await pipeline.run(query="What is Python?")

        end_time = time.time()
        duration = end_time - start_time

        # Pipeline should complete quickly (< 1 second for simple case)
        assert duration < 1.0
        assert context.total_duration_ms >= 0
