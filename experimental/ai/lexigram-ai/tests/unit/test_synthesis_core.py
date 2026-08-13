"""Tests for response synthesis: synthesizers, quality control, and formatters."""

from __future__ import annotations

from lexigram.ai.llm.types import Completion
import pytest
from lexigram.ai.llm.types import Completion

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
