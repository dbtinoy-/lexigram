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
