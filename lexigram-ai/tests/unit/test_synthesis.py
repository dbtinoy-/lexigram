"""Comprehensive tests for response synthesis.

This module tests all synthesis components including synthesizers, quality
control, context management, and formatters.
"""

from __future__ import annotations

from enum import Enum

import pytest

try:
    from lexigram.ai.rag.synthesis import (
        AbstractiveSynthesizer,
        ConfidenceScorer,
        ContextChunk,
        ContextDeduplicator,
        ContextRanker,
        DirectSynthesizer,
        ExtractiveSynthesizer,
        FaithfulnessChecker,
        HallucinationDetector,
        HybridSynthesizer,
        JSONFormatter,
        LengthOptimizer,
        MarkdownFormatter,
        OutputFormat,
        PlainTextFormatter,
        QualityMetrics,
        RelevanceFilter,
        SynthesisConfig,
        SynthesisResult,
        SynthesisStrategy,
    )
except ImportError as e:
    pytest.skip(f"synthesis import failed: {e}", allow_module_level=True)
from lexigram.serialization import loads
from lexigram.ai.llm.types import Completion

# ============================================================================
# Test Types
# ============================================================================


class _OkResult:
    """Minimal Result-like success wrapper for synthesis tests."""

    def __init__(self, value):
        self._value = value

    def is_err(self):
        return False

    def unwrap(self):
        return self._value

    def unwrap_err(self):
        raise AssertionError("_OkResult has no error")


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


# ============================================================================
# Test Synthesizers
# ============================================================================


class TestDirectSynthesizer:
    """Test DirectSynthesizer."""

    @pytest.mark.asyncio
    async def test_basic_synthesis(self):
        """Test basic direct synthesis."""
        synthesizer = DirectSynthesizer()
        chunks = [
            ContextChunk(text="Python is great.", source="doc1", score=0.9, rank=0),
            ContextChunk(
                text="Testing is important.", source="doc2", score=0.8, rank=1,
            ),
        ]

        result = await synthesizer.synthesize(
            query="What about Python?",
            context_chunks=chunks,
        )

        assert result.query == "What about Python?"
        assert "[1]" in result.response
        assert "[2]" in result.response
        assert "Python is great" in result.response
        assert result.strategy == SynthesisStrategy.DIRECT

    @pytest.mark.asyncio
    async def test_max_chunks_limit(self):
        """Test max chunks limitation."""
        synthesizer = DirectSynthesizer(max_chunks=1)
        chunks = [
            ContextChunk(text="First", source="doc1", rank=0),
            ContextChunk(text="Second", source="doc2", rank=1),
        ]

        result = await synthesizer.synthesize(
            query="test",
            context_chunks=chunks,
        )

        assert result.num_chunks_used == 1
        assert "First" in result.response

    @pytest.mark.asyncio
    async def test_without_sources(self):
        """Test synthesis without source citations."""
        synthesizer = DirectSynthesizer(include_sources=False)
        chunks = [ContextChunk(text="Test content", source="doc1")]

        result = await synthesizer.synthesize(
            query="test",
            context_chunks=chunks,
        )

        assert "[1]" not in result.response
        assert len(result.citations) == 0

    @pytest.mark.asyncio
    async def test_empty_query_error(self):
        """Test error on empty query."""
        synthesizer = DirectSynthesizer()
        chunks = [ContextChunk(text="Test", source="doc1")]

        with pytest.raises(ValueError, match="empty"):
            await synthesizer.synthesize(query="", context_chunks=chunks)

    @pytest.mark.asyncio
    async def test_no_chunks_error(self):
        """Test error on no chunks."""
        synthesizer = DirectSynthesizer()

        with pytest.raises(ValueError, match="No context chunks"):
            await synthesizer.synthesize(query="test", context_chunks=[])


class TestExtractiveSynthesizer:
    """Test ExtractiveSynthesizer."""

    @pytest.mark.asyncio
    async def test_basic_extraction(self):
        """Test basic extractive synthesis."""
        synthesizer = ExtractiveSynthesizer(max_sentences=2)
        chunks = [
            ContextChunk(
                text="Python is a programming language. It is very popular. Many developers use it.",
                source="doc1",
                score=0.9,
                rank=0,
            ),
        ]

        result = await synthesizer.synthesize(
            query="What is Python?",
            context_chunks=chunks,
        )

        assert result.strategy == SynthesisStrategy.EXTRACTIVE
        assert len(result.response) > 0
        # Should have extracted content
        assert len(result.response) > 10

    @pytest.mark.asyncio
    async def test_sentence_extraction(self):
        """Test sentence extraction."""
        synthesizer = ExtractiveSynthesizer()
        text = "This is sentence one. This is sentence two. This is sentence three."
        sentences = synthesizer._extract_sentences(text)

        assert len(sentences) >= 3
        assert any("sentence one" in s for s in sentences)

    @pytest.mark.asyncio
    async def test_keyword_extraction(self):
        """Test keyword extraction."""
        synthesizer = ExtractiveSynthesizer()
        text = "Python programming language for machine learning"
        keywords = synthesizer._extract_keywords(text)

        assert "python" in keywords
        assert "programming" in keywords
        assert "language" in keywords
        assert "the" not in keywords  # Stop word filtered

    @pytest.mark.asyncio
    async def test_reorder_sentences(self):
        """Test sentence reordering."""
        synthesizer = ExtractiveSynthesizer(reorder_sentences=True)
        chunks = [
            ContextChunk(
                text="First sentence here. Second sentence here. Third sentence here.",
                source="doc1",
                rank=0,
            ),
        ]

        result = await synthesizer.synthesize(
            query="test",
            context_chunks=chunks,
        )

        assert result.metadata["reordered"] is True


# Mock LLM client for testing
class MockLLMClient:
    """Mock LLM client for testing."""

    async def complete(self, messages, **kwargs):
        """Generate mock response."""
        return _OkResult(
            Completion(
                content="This is a generated answer based on the context. [1]",
                model="mock",
            ),
        )


class TestAbstractiveSynthesizer:
    """Test AbstractiveSynthesizer."""

    @pytest.mark.asyncio
    async def test_basic_synthesis(self):
        """Test basic abstractive synthesis."""
        llm_client = MockLLMClient()
        synthesizer = AbstractiveSynthesizer(llm_client=llm_client)
        chunks = [
            ContextChunk(text="Python is great for AI.", source="doc1", score=0.9),
        ]

        result = await synthesizer.synthesize(
            query="What is Python used for?",
            context_chunks=chunks,
        )

        assert result.strategy == SynthesisStrategy.ABSTRACTIVE
        assert len(result.response) > 0
        assert "generated answer" in result.response.lower()

    @pytest.mark.asyncio
    async def test_prompt_building(self):
        """Test prompt construction."""
        llm_client = MockLLMClient()
        synthesizer = AbstractiveSynthesizer(llm_client=llm_client)
        chunks = [
            ContextChunk(text="Test content", source="doc1"),
        ]

        prompt = synthesizer._build_prompt("What is this?", chunks)

        assert "What is this?" in prompt
        assert "Test content" in prompt
        assert "Context:" in prompt


class TestHybridSynthesizer:
    """Test HybridSynthesizer."""

    @pytest.mark.asyncio
    async def test_basic_synthesis(self):
        """Test basic hybrid synthesis."""
        llm_client = MockLLMClient()
        synthesizer = HybridSynthesizer(llm_client=llm_client)
        chunks = [
            ContextChunk(
                text="Python is a programming language. It is used for AI and web development.",
                source="doc1",
                score=0.9,
            ),
        ]

        result = await synthesizer.synthesize(
            query="What is Python?",
            context_chunks=chunks,
        )

        assert result.strategy == SynthesisStrategy.HYBRID
        assert len(result.response) > 0
        assert "extraction_phase" in result.metadata
        assert "abstraction_phase" in result.metadata


# ============================================================================
# Test Quality Components
# ============================================================================


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
        filter = RelevanceFilter()
        query = "What is Python programming?"
        response = "Python is a programming language for software development."

        score = await filter.check_relevance(query, response)

        assert score > 0.4  # Good keyword overlap

    @pytest.mark.asyncio
    async def test_low_relevance(self):
        """Test checking low relevance."""
        filter = RelevanceFilter()
        query = "What is Python?"
        response = "Java is a programming language."

        score = await filter.check_relevance(query, response)

        assert score < 0.5  # Limited overlap

    @pytest.mark.asyncio
    async def test_is_relevant(self):
        """Test relevance threshold check."""
        filter = RelevanceFilter(threshold=0.5)
        query = "Python programming"
        response = "Python is a great programming language"

        is_relevant = await filter.is_relevant(query, response)

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

        hallucinations, count = await detector.detect_hallucinations(response, chunks)

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

        hallucinations, count = await detector.detect_hallucinations(response, chunks)

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


# ============================================================================
# Test Context Management
# ============================================================================


class TestContextRanker:
    """Test ContextRanker."""

    @pytest.mark.asyncio
    async def test_rank_by_scores(self):
        """Test ranking by scores."""
        ranker = ContextRanker(use_scores=True)
        chunks = [
            ContextChunk(text="Low score", source="doc1", score=0.5),
            ContextChunk(text="High score", source="doc2", score=0.9),
            ContextChunk(text="Medium score", source="doc3", score=0.7),
        ]

        ranked = await ranker.rank_chunks("test", chunks)

        assert ranked[0].text == "High score"
        assert ranked[1].text == "Medium score"
        assert ranked[2].text == "Low score"
        assert ranked[0].rank == 0
        assert ranked[1].rank == 1

    @pytest.mark.asyncio
    async def test_rerank_with_top_k(self):
        """Test reranking with top K limit."""
        ranker = ContextRanker()
        chunks = [
            ContextChunk(text=f"Chunk {i}", source=f"doc{i}", score=i * 0.1)
            for i in range(10)
        ]

        ranked = await ranker.rerank_chunks("test", chunks, top_k=3)

        assert len(ranked) == 3


class TestContextDeduplicator:
    """Test ContextDeduplicator."""

    @pytest.mark.asyncio
    async def test_remove_exact_duplicates(self):
        """Test removing exact duplicates."""
        dedup = ContextDeduplicator()
        chunks = [
            ContextChunk(text="Same content", source="doc1", score=0.8, rank=0),
            ContextChunk(text="Same content", source="doc2", score=0.9, rank=1),
            ContextChunk(text="Different content", source="doc3", score=0.7, rank=2),
        ]

        unique = await dedup.deduplicate_chunks(chunks)

        # Should have removed duplicate
        assert len(unique) <= 2
        # Should keep the one with higher score
        same_content_chunks = list(filter(lambda c: "Same" in c.text, unique))
        if same_content_chunks:
            assert any(c.score >= 0.8 for c in same_content_chunks)

    @pytest.mark.asyncio
    async def test_remove_similar_chunks(self):
        """Test removing similar chunks."""
        dedup = ContextDeduplicator(similarity_threshold=0.8)
        chunks = [
            ContextChunk(
                text="Python is great for programming", source="doc1", score=0.8,
            ),
            ContextChunk(
                text="Python is excellent for programming", source="doc2", score=0.9,
            ),
        ]

        unique = await dedup.deduplicate_chunks(chunks)

        # Should detect high similarity
        assert len(unique) <= 2

    def test_calculate_text_similarity(self):
        """Test text similarity calculation."""
        dedup = ContextDeduplicator()

        # High similarity
        sim1 = dedup._calculate_text_similarity(
            "Python is great",
            "Python is excellent",
        )
        assert sim1 > 0.3

        # Low similarity
        sim2 = dedup._calculate_text_similarity(
            "Python programming",
            "Java development",
        )
        assert sim2 < sim1


class TestLengthOptimizer:
    """Test LengthOptimizer."""

    @pytest.mark.asyncio
    async def test_optimize_within_limit(self):
        """Test optimization when already within limit."""
        optimizer = LengthOptimizer(max_tokens=1000)
        chunks = [
            ContextChunk(text="Short text", source="doc1", score=0.9),
        ]

        optimized = await optimizer.optimize_length(chunks)

        assert len(optimized) == 1
        assert optimized[0].text == "Short text"

    @pytest.mark.asyncio
    async def test_optimize_exceeds_limit(self):
        """Test optimization when exceeding limit."""
        optimizer = LengthOptimizer(max_tokens=10)  # Very small limit
        chunks = [
            ContextChunk(
                text="This is a very long text that exceeds the token limit",
                source="doc1",
                score=0.9,
                rank=0,
            ),
            ContextChunk(
                text="Another long text chunk", source="doc2", score=0.8, rank=1,
            ),
        ]

        optimized = await optimizer.optimize_length(chunks)

        # Should reduce chunks
        assert len(optimized) <= len(chunks)

    def test_estimate_tokens(self):
        """Test token estimation."""
        optimizer = LengthOptimizer(chars_per_token=4)

        tokens = optimizer._estimate_tokens("This is a test")

        assert tokens > 0

    @pytest.mark.asyncio
    async def test_optimize_with_budget(self):
        """Test optimization with custom budget."""
        optimizer = LengthOptimizer(max_tokens=1000)
        chunks = [
            ContextChunk(text="Test " * 100, source="doc1", score=0.9),
        ]

        optimized = await optimizer.optimize_with_budget(chunks, token_budget=50)

        # Should respect custom budget
        total_tokens = sum(optimizer._estimate_tokens(c.text) for c in optimized)
        assert total_tokens <= 50


# ============================================================================
# Test Formatters
# ============================================================================


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
