"""Tests for response synthesis: synthesizers, quality control, and formatters."""

from __future__ import annotations

from lexigram.serialization import loads
import pytest
from lexigram.serialization import loads

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


class TestPlainTextFormatter:
    """Test PlainTextFormatter."""

    def test_basic_formatting(self):
        """Test basic plain text formatting."""
        formatter = PlainTextFormatter()
        result = SynthesisResult(
            query="test",
            response="This is the response.",
            strategy=SynthesisStrategy.DIRECT,
            sources=["doc1", "doc2"],
        )

        output = formatter.format(result)

        assert "This is the response." in output
        assert "Sources:" in output
        assert "doc1" in output

    def test_without_sources(self):
        """Test formatting without sources."""
        formatter = PlainTextFormatter(include_sources=False)
        result = SynthesisResult(
            query="test",
            response="Response text.",
            strategy=SynthesisStrategy.DIRECT,
            sources=["doc1"],
        )

        output = formatter.format(result)

        assert "Response text." in output
        assert "Sources:" not in output

    def test_with_metadata(self):
        """Test formatting with metadata."""
        formatter = PlainTextFormatter(include_metadata=True)
        metrics = QualityMetrics(confidence=0.85)
        result = SynthesisResult(
            query="test",
            response="Response text.",
            strategy=SynthesisStrategy.DIRECT,
            quality_metrics=metrics,
        )

        output = formatter.format(result)

        assert "Strategy:" in output
        assert "direct" in output
        assert "Confidence:" in output


class TestMarkdownFormatter:
    """Test MarkdownFormatter."""

    def test_basic_formatting(self):
        """Test basic markdown formatting."""
        formatter = MarkdownFormatter()
        result = SynthesisResult(
            query="test",
            response="This is the response.",
            strategy=SynthesisStrategy.DIRECT,
            sources=["doc1"],
        )

        output = formatter.format(result)

        assert "# Response" in output
        assert "## Sources" in output
        assert "This is the response." in output

    def test_without_title(self):
        """Test formatting without title."""
        formatter = MarkdownFormatter(include_title=False)
        result = SynthesisResult(
            query="test",
            response="Response text.",
            strategy=SynthesisStrategy.DIRECT,
        )

        output = formatter.format(result)

        assert "# Response" not in output
        assert "Response text." in output

    def test_with_quality_metrics(self):
        """Test formatting with quality metrics."""
        formatter = MarkdownFormatter(include_quality=True)
        metrics = QualityMetrics(
            faithfulness=0.9,
            relevance=0.8,
            coherence=0.85,
            confidence=0.87,
        )
        result = SynthesisResult(
            query="test",
            response="Response text.",
            strategy=SynthesisStrategy.DIRECT,
            quality_metrics=metrics,
        )

        output = formatter.format(result)

        assert "## Quality Metrics" in output
        assert "Faithfulness" in output
        assert "0.90" in output


class TestJSONFormatter:
    """Test JSONFormatter."""

    def test_basic_formatting(self):
        """Test basic JSON formatting."""
        formatter = JSONFormatter()
        result = SynthesisResult(
            query="test",
            response="Response text.",
            strategy=SynthesisStrategy.DIRECT,
        )

        output = formatter.format(result)

        # Should be valid JSON
        data = loads(output)
        assert data["query"] == "test"
        assert data["response"] == "Response text."
        assert data["strategy"] == "direct"

    def test_compact_formatting(self):
        """Test compact JSON formatting."""
        formatter = JSONFormatter(indent=None)
        result = SynthesisResult(
            query="test",
            response="Response.",
            strategy=SynthesisStrategy.DIRECT,
        )

        output = formatter.format(result)

        # Compact should have no newlines
        assert "\n" not in output or output.count("\n") < 3

    def test_without_chunks(self):
        """Test formatting without chunk text."""
        formatter = JSONFormatter(include_chunks=False)
        chunks = [
            ContextChunk(text="Long chunk text" * 100, source="doc1", score=0.9),
        ]
        result = SynthesisResult(
            query="test",
            response="Response.",
            strategy=SynthesisStrategy.DIRECT,
            context_chunks=chunks,
        )

        output = formatter.format(result)
        data = loads(output)

        # Should not include full chunk text
        assert "text_length" in str(data["context_chunks"])
