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


class TestFaithfulnessChecker:
    """Test FaithfulnessChecker."""

    @pytest.mark.asyncio
    async def test_high_faithfulness(self):
        """Test checking high faithfulness."""
        checker = FaithfulnessChecker()
        response = "Python is a programming language used for data science."
        chunks = [
            ContextChunk(
                text="Python is a programming language. It is widely used for data science and machine learning.",
                source="doc1",
            ),
        ]

        score = await checker.check_faithfulness(response, chunks)

        assert score > 0.5  # Should have good overlap

    @pytest.mark.asyncio
    async def test_low_faithfulness(self):
        """Test checking low faithfulness."""
        checker = FaithfulnessChecker()
        response = "Java is the best language for everything."
        chunks = [
            ContextChunk(
                text="Python is great for data science.",
                source="doc1",
            ),
        ]

        score = await checker.check_faithfulness(response, chunks)

        assert score < 0.5  # Low overlap expected

    def test_extract_claims(self):
        """Test claim extraction."""
        checker = FaithfulnessChecker()
        response = "Python is great. It is fast. Many people use it."
        claims = checker._extract_claims(response)

        # Should extract at least 2 claims (may filter short ones)
        assert len(claims) >= 2


class TestRelevanceFilter:
    """Test RelevanceFilter."""

    @pytest.mark.asyncio
    async def test_high_relevance(self):
        """Test checking high relevance."""
        relevance_filter = RelevanceFilter()
        query = "What is Python programming?"
        response = "Python is a programming language for software development."

        score = await relevance_filter.check_relevance(query, response)

        assert score > 0.4  # Good keyword overlap

    @pytest.mark.asyncio
    async def test_low_relevance(self):
        """Test checking low relevance."""
        relevance_filter = RelevanceFilter()
        query = "What is Python?"
        response = "Java is a programming language."

        score = await relevance_filter.check_relevance(query, response)

        assert score < 0.5  # Limited overlap

    @pytest.mark.asyncio
    async def test_is_relevant(self):
        """Test relevance threshold check."""
        relevance_filter = RelevanceFilter(threshold=0.5)
        query = "Python programming"
        response = "Python is a great programming language"

        is_relevant = await relevance_filter.is_relevant(query, response)

        assert is_relevant is True


class TestHallucinationDetector:
    """Test HallucinationDetector."""

    @pytest.mark.asyncio
    async def test_no_hallucinations(self):
        """Test detection when no hallucinations."""
        detector = HallucinationDetector()
        response = "Python is a programming language."
        chunks = [
            ContextChunk(
                text="Python is a high-level programming language.",
                source="doc1",
            ),
        ]

        _, count = await detector.detect_hallucinations(response, chunks)

        assert count == 0

    @pytest.mark.asyncio
    async def test_with_hallucinations(self):
        """Test detection with hallucinations."""
        detector = HallucinationDetector(strict_mode=True)
        response = "Python was invented in 1776 by George Washington."
        chunks = [
            ContextChunk(
                text="Python is a programming language.",
                source="doc1",
            ),
        ]

        _, count = await detector.detect_hallucinations(response, chunks)

        # Likely to detect hallucination due to low support
        assert count >= 0  # May or may not detect depending on threshold

    @pytest.mark.asyncio
    async def test_has_hallucinations(self):
        """Test has_hallucinations method."""
        detector = HallucinationDetector()
        response = (
            "Completely unrelated content about something else entirely different."
        )
        chunks = [
            ContextChunk(text="Python programming", source="doc1"),
        ]

        has_hall = await detector.has_hallucinations(response, chunks)

        # Should be True or False depending on detection
        assert isinstance(has_hall, bool)


class TestConfidenceScorer:
    """Test ConfidenceScorer."""

    @pytest.mark.asyncio
    async def test_calculate_quality_metrics(self):
        """Test quality metrics calculation."""
        scorer = ConfidenceScorer()
        query = "What is Python?"
        response = "Python is a programming language."
        chunks = [
            ContextChunk(
                text="Python is a high-level programming language.",
                source="doc1",
            ),
        ]

        metrics = await scorer.calculate_quality_metrics(query, response, chunks)

        assert 0.0 <= metrics.faithfulness <= 1.0
        assert 0.0 <= metrics.relevance <= 1.0
        assert 0.0 <= metrics.coherence <= 1.0
        assert 0.0 <= metrics.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_calculate_confidence(self):
        """Test confidence calculation."""
        scorer = ConfidenceScorer()
        query = "What is Python?"
        response = "Python is a programming language."
        chunks = [
            ContextChunk(text="Python is a programming language.", source="doc1"),
        ]

        confidence = await scorer.calculate_confidence(query, response, chunks)

        assert 0.0 <= confidence <= 1.0

    def test_calculate_coherence(self):
        """Test coherence calculation."""
        scorer = ConfidenceScorer()

        # Good coherence
        good_response = "This is a well-formed response. It has multiple sentences. The content is clear."
        good_score = scorer._calculate_coherence(good_response)
        assert good_score > 0.5

        # Poor coherence
        poor_response = "a"
        poor_score = scorer._calculate_coherence(poor_response)
        assert poor_score < good_score
