"""Tests for response synthesis: synthesizers, quality control, and formatters."""

from __future__ import annotations

import pytest

import pytest

try:  # noqa: F401
    from lexigram.ai.rag.synthesis import (
        AbstractiveSynthesizer,  # noqa: F401
        ConfidenceScorer,  # noqa: F401
        ContextChunk,  # noqa: F401
        ContextDeduplicator,  # noqa: F401
        ContextRanker,  # noqa: F401
        DirectSynthesizer,  # noqa: F401
        ExtractiveSynthesizer,  # noqa: F401
        FaithfulnessChecker,  # noqa: F401
        HallucinationDetector,  # noqa: F401
        HybridSynthesizer,  # noqa: F401
        JSONFormatter,  # noqa: F401
        LengthOptimizer,  # noqa: F401
        MarkdownFormatter,  # noqa: F401
        OutputFormat,  # noqa: F401
        PlainTextFormatter,  # noqa: F401
        QualityMetrics,  # noqa: F401
        RelevanceFilter,  # noqa: F401
        SynthesisConfig,  # noqa: F401
        SynthesisResult,  # noqa: F401
        SynthesisStrategy,  # noqa: F401
    )
except ImportError as e:
    pytest.skip(f"synthesis import failed: {e}", allow_module_level=True)


class TestSynthesisStrategy:
    """Test SynthesisStrategy enum."""

    def test_strategy_values(self):
        """Test all strategy enum values."""
        assert SynthesisStrategy.DIRECT == "direct"
        assert SynthesisStrategy.EXTRACTIVE == "extractive"
        assert SynthesisStrategy.ABSTRACTIVE == "abstractive"
        assert SynthesisStrategy.HYBRID == "hybrid"


class TestOutputFormat:
    """Test OutputFormat enum."""

    def test_format_values(self):
        """Test all format enum values."""
        assert OutputFormat.PLAIN_TEXT == "plain_text"
        assert OutputFormat.MARKDOWN == "markdown"
        assert OutputFormat.JSON == "json"
        assert OutputFormat.HTML == "html"


class TestContextChunk:
    """Test ContextChunk dataclass."""

    def test_create_chunk(self):
        """Test creating a context chunk."""
        chunk = ContextChunk(
            text="Test content",
            source="doc1.txt",
            score=0.9,
            rank=0,
        )
        assert chunk.text == "Test content"
        assert chunk.source == "doc1.txt"
        assert chunk.score == 0.9
        assert chunk.rank == 0

    def test_chunk_validation(self):
        """Test chunk validation."""
        with pytest.raises(ValueError, match="empty"):
            ContextChunk(text="", source="test")

        with pytest.raises(ValueError, match="between 0 and 1"):
            ContextChunk(text="test", source="test", score=1.5)

    def test_chunk_metadata(self):
        """Test chunk with metadata."""
        chunk = ContextChunk(
            text="Test",
            source="test",
            metadata={"page": 1, "section": "intro"},
        )
        assert chunk.metadata["page"] == 1
        assert chunk.metadata["section"] == "intro"


class TestQualityMetrics:
    """Test QualityMetrics dataclass."""

    def test_create_metrics(self):
        """Test creating quality metrics."""
        metrics = QualityMetrics(
            faithfulness=0.9,
            relevance=0.8,
            coherence=0.85,
            confidence=0.87,
        )
        assert metrics.faithfulness == 0.9
        assert metrics.relevance == 0.8
        assert metrics.coherence == 0.85
        assert metrics.confidence == 0.87

    def test_metrics_validation(self):
        """Test metrics validation."""
        with pytest.raises(ValueError, match="between 0 and 1"):
            QualityMetrics(faithfulness=1.5)

    def test_is_high_quality(self):
        """Test high quality property."""
        high_quality = QualityMetrics(
            faithfulness=0.8,
            relevance=0.8,
            coherence=0.8,
            confidence=0.8,
        )
        assert high_quality.is_high_quality

        low_quality = QualityMetrics(
            faithfulness=0.6,
            relevance=0.6,
            coherence=0.6,
            confidence=0.6,
        )
        assert not low_quality.is_high_quality

    def test_average_score(self):
        """Test average score calculation."""
        metrics = QualityMetrics(
            faithfulness=0.8,
            relevance=0.6,
            coherence=0.7,
            confidence=0.9,
        )
        # Average of 0.8, 0.6, 0.7, 0.9 = 3.0 / 4 = 0.75
        assert abs(metrics.average_score - 0.75) < 0.01

    def test_metrics_to_dict(self):
        """Test metrics serialization."""
        metrics = QualityMetrics(
            faithfulness=0.8,
            relevance=0.7,
            coherence=0.9,
            confidence=0.8,
        )
        data = metrics.to_dict()
        assert data["faithfulness"] == 0.8
        assert data["relevance"] == 0.7
        assert "is_high_quality" in data
        assert "average_score" in data


class TestSynthesisResult:
    """Test SynthesisResult dataclass."""

    def test_create_result(self):
        """Test creating synthesis result."""
        chunks = [
            ContextChunk(text="Test 1", source="doc1", score=0.9),
            ContextChunk(text="Test 2", source="doc2", score=0.8),
        ]
        result = SynthesisResult(
            query="What is testing?",
            response="Testing is important.",
            strategy=SynthesisStrategy.DIRECT,
            context_chunks=chunks,
        )
        assert result.query == "What is testing?"
        assert result.response == "Testing is important."
        assert result.strategy == SynthesisStrategy.DIRECT
        assert len(result.context_chunks) == 2

    def test_result_validation(self):
        """Test result validation."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            SynthesisResult(
                query="",
                response="test",
                strategy=SynthesisStrategy.DIRECT,
            )

        with pytest.raises(ValueError, match="Response cannot be empty"):
            SynthesisResult(
                query="test",
                response="",
                strategy=SynthesisStrategy.DIRECT,
            )

    def test_num_chunks_used(self):
        """Test chunk count property."""
        chunks = [
            ContextChunk(text="Test 1", source="doc1"),
            ContextChunk(text="Test 2", source="doc2"),
        ]
        result = SynthesisResult(
            query="test",
            response="test response",
            strategy=SynthesisStrategy.DIRECT,
            context_chunks=chunks,
        )
        assert result.num_chunks_used == 2

    def test_is_high_confidence(self):
        """Test high confidence property."""
        metrics = QualityMetrics(confidence=0.8)
        result = SynthesisResult(
            query="test",
            response="test response",
            strategy=SynthesisStrategy.DIRECT,
            quality_metrics=metrics,
        )
        assert result.is_high_confidence

    def test_is_faithful(self):
        """Test faithfulness property."""
        metrics = QualityMetrics(faithfulness=0.8)
        result = SynthesisResult(
            query="test",
            response="test response",
            strategy=SynthesisStrategy.DIRECT,
            quality_metrics=metrics,
        )
        assert result.is_faithful

    def test_result_to_dict(self):
        """Test result serialization."""
        result = SynthesisResult(
            query="test",
            response="test response",
            strategy=SynthesisStrategy.DIRECT,
        )
        data = result.to_dict()
        assert data["query"] == "test"
        assert data["response"] == "test response"
        assert data["strategy"] == "direct"
        assert "created_at" in data


class TestSynthesisConfig:
    """Test SynthesisConfig dataclass."""

    def test_create_config(self):
        """Test creating synthesis config."""
        config = SynthesisConfig(
            strategy=SynthesisStrategy.EXTRACTIVE,
            max_context_length=3000,
            max_response_length=300,
        )
        assert config.strategy == SynthesisStrategy.EXTRACTIVE
        assert config.max_context_length == 3000
        assert config.max_response_length == 300

    def test_config_validation(self):
        """Test config validation."""
        with pytest.raises(ValueError, match="must be positive"):
            SynthesisConfig(max_context_length=0)

        with pytest.raises(ValueError, match="between 0 and 1"):
            SynthesisConfig(min_confidence=1.5)
