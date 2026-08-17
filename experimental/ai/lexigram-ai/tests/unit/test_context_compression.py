"""Tests for context compression."""

from __future__ import annotations

from enum import Enum

import pytest

try:
    from lexigram.ai.rag.context_compression import (
        AbstractiveCompressor,
        CompressionResult,
        CompressionStrategy,
        ExtractiveSummaryCompressor,
        HybridCompressor,
        SemanticDeduplicationCompressor,
        TokenLimitCompressor,
        compress_context,
    )
except ImportError as e:
    pytest.skip(f"context_compression import failed: {e}", allow_module_level=True)


# Mock LLM Client
class MockLLMClient:
    """Mock LLM client for testing."""

    def __init__(self, responses=None):
        self.responses = responses or []
        self.call_count = 0

    async def complete(self, messages, temperature=0.7, max_tokens=None):
        """Return mock response."""
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return MockResponse(response)
        return MockResponse("This is a concise summary of the main points.")


class MockResponse:
    """Mock response object."""

    def __init__(self, content):
        self.content = content

    def is_err(self):
        return False

    def unwrap(self):
        return self

    def unwrap_err(self):
        raise AssertionError("MockResponse has no error")


# Sample texts for testing
SAMPLE_TEXT = """
Machine learning is a subset of artificial intelligence. Machine learning algorithms
build models based on sample data. These models can make predictions or decisions
without being explicitly programmed. Machine learning is used in many applications.
Common applications include email filtering and computer vision. Machine learning
has become increasingly important in modern technology.
"""

LONG_TEXT = """
Artificial intelligence (AI) is intelligence demonstrated by machines. AI research
has been defined as the field of study of intelligent agents. An intelligent agent
is a system that perceives its environment and takes actions. These actions maximize
the agent's chance of successfully achieving its goals.

Machine learning is a subset of artificial intelligence. It focuses on the use of
data and algorithms. Machine learning algorithms build models based on sample data.
These models can make predictions or decisions without being explicitly programmed
to do so. Machine learning algorithms are used in a wide variety of applications.

Deep learning is a subset of machine learning. It uses neural networks with multiple
layers. These neural networks are inspired by the human brain. Deep learning has been
applied to fields including computer vision and natural language processing. Deep
learning has produced results comparable to human expert performance in some domains.

The history of artificial intelligence began in antiquity. AI research was founded
as an academic discipline in 1956. In the decades since then, AI has experienced
several waves of optimism. These waves were followed by disappointment and loss of
funding. AI research has made significant progress in the 21st century. Modern AI
techniques have become essential parts of the technology industry.
"""


# Tests for CompressionResult
class TestCompressionResult:
    """Tests for CompressionResult."""

    def test_creation(self):
        """Test creating compression result."""
        result = CompressionResult(
            original_text="Original text here",
            compressed_text="Compressed",
            original_tokens=100,
            compressed_tokens=50,
            compression_ratio=0.5,
            strategy=CompressionStrategy.EXTRACTIVE,
        )

        assert result.original_text == "Original text here"
        assert result.compressed_text == "Compressed"
        assert result.original_tokens == 100
        assert result.compressed_tokens == 50
        assert result.compression_ratio == 0.5
        assert result.strategy == CompressionStrategy.EXTRACTIVE

    def test_token_savings(self):
        """Test token savings calculation."""
        result = CompressionResult(
            original_text="text",
            compressed_text="txt",
            original_tokens=100,
            compressed_tokens=40,
            compression_ratio=0.4,
            strategy=CompressionStrategy.EXTRACTIVE,
        )

        assert result.token_savings == 60
        assert result.savings_percentage == 60.0

    def test_zero_tokens(self):
        """Test with zero original tokens."""
        result = CompressionResult(
            original_text="",
            compressed_text="",
            original_tokens=0,
            compressed_tokens=0,
            compression_ratio=1.0,
            strategy=CompressionStrategy.EXTRACTIVE,
        )

        assert result.savings_percentage == 0.0

    def test_repr(self):
        """Test string representation."""
        result = CompressionResult(
            original_text="text",
            compressed_text="txt",
            original_tokens=100,
            compressed_tokens=50,
            compression_ratio=0.5,
            strategy=CompressionStrategy.EXTRACTIVE,
        )

        repr_str = repr(result)
        assert "ratio=0.50" in repr_str
        assert "100→50" in repr_str


# Tests for ExtractiveSummaryCompressor
class TestExtractiveSummaryCompressor:
    """Tests for ExtractiveSummaryCompressor."""

    @pytest.mark.asyncio
    async def test_creation(self):
        """Test creating extractive compressor."""
        compressor = ExtractiveSummaryCompressor(
            max_sentences=3,
            query_weight=0.7,
            position_weight=0.3,
        )

        assert compressor.max_sentences == 3
        assert compressor.query_weight == 0.7
        assert compressor.position_weight == 0.3

    @pytest.mark.asyncio
    async def test_compress_short_text(self):
        """Test compressing text shorter than max_sentences."""
        compressor = ExtractiveSummaryCompressor(max_sentences=10)
        result = await compressor.compress("Short text. Very short.")

        assert result.original_text == result.compressed_text
        assert result.compression_ratio == 1.0

    @pytest.mark.asyncio
    async def test_compress_long_text(self):
        """Test compressing longer text."""
        compressor = ExtractiveSummaryCompressor(max_sentences=2)
        result = await compressor.compress(SAMPLE_TEXT)

        assert result.compressed_tokens < result.original_tokens
        assert result.compression_ratio < 1.0
        assert result.strategy == CompressionStrategy.EXTRACTIVE

    @pytest.mark.asyncio
    async def test_compress_with_query(self):
        """Test compression with query relevance."""
        compressor = ExtractiveSummaryCompressor(max_sentences=2)
        result = await compressor.compress(
            SAMPLE_TEXT,
            query="What are common applications?",
        )

        # Should include sentence about applications
        assert "applications" in result.compressed_text.lower()
        assert result.metadata["query_used"] is True

    @pytest.mark.asyncio
    async def test_compress_list_context(self):
        """Test compressing list of texts."""
        compressor = ExtractiveSummaryCompressor(max_sentences=2)
        context = ["First text here.", "Second text here.", "Third text here."]

        result = await compressor.compress(context)

        assert (
            result.original_text
            == "First text here.\n\nSecond text here.\n\nThird text here."
        )
        # With only 3 sentences and max_sentences=2, should compress
        assert len(result.compressed_text) <= len(result.original_text)

    @pytest.mark.asyncio
    async def test_metadata(self):
        """Test metadata in result."""
        compressor = ExtractiveSummaryCompressor(max_sentences=2)
        result = await compressor.compress(SAMPLE_TEXT)

        assert "total_sentences" in result.metadata
        assert "selected_sentences" in result.metadata
        assert "timestamp" in result.metadata


# Tests for AbstractiveCompressor
class TestAbstractiveCompressor:
    """Tests for AbstractiveCompressor."""

    @pytest.mark.asyncio
    async def test_creation(self):
        """Test creating abstractive compressor."""
        llm = MockLLMClient()
        compressor = AbstractiveCompressor(llm_client=llm, max_tokens=100)

        assert compressor.max_tokens == 100
        assert compressor.temperature == 0.3

    @pytest.mark.asyncio
    async def test_compress(self):
        """Test LLM-based compression."""
        llm = MockLLMClient(responses=["AI is machine intelligence for automation."])
        compressor = AbstractiveCompressor(llm_client=llm, max_tokens=50)

        result = await compressor.compress(LONG_TEXT)

        assert result.strategy == CompressionStrategy.ABSTRACTIVE
        assert result.compressed_text == "AI is machine intelligence for automation."
        assert llm.call_count == 1

    @pytest.mark.asyncio
    async def test_compress_with_query(self):
        """Test compression with query focus."""
        llm = MockLLMClient(
            responses=["Machine learning builds models from data for predictions."],
        )
        compressor = AbstractiveCompressor(llm_client=llm)

        result = await compressor.compress(
            LONG_TEXT,
            query="What is machine learning?",
        )

        assert "learning" in result.compressed_text.lower()
        assert result.metadata["query_used"] is True

    @pytest.mark.asyncio
    async def test_metadata(self):
        """Test metadata in result."""
        llm = MockLLMClient()
        compressor = AbstractiveCompressor(
            llm_client=llm, max_tokens=100, temperature=0.5,
        )

        result = await compressor.compress(SAMPLE_TEXT)

        assert result.metadata["max_tokens"] == 100
        assert result.metadata["temperature"] == 0.5
        assert "timestamp" in result.metadata


# Tests for TokenLimitCompressor
class TestTokenLimitCompressor:
    """Tests for TokenLimitCompressor."""

    @pytest.mark.asyncio
    async def test_creation(self):
        """Test creating token limit compressor."""
        compressor = TokenLimitCompressor(max_tokens=500, preserve_end=True)

        assert compressor.max_tokens == 500
        assert compressor.preserve_end is True

    @pytest.mark.asyncio
    async def test_compress_short_text(self):
        """Test compressing text within limit."""
        compressor = TokenLimitCompressor(max_tokens=1000)
        result = await compressor.compress(SAMPLE_TEXT)

        # Text is short enough
        assert result.compressed_text == result.original_text
        assert result.compression_ratio == 1.0

    @pytest.mark.asyncio
    async def test_compress_long_text_beginning_only(self):
        """Test truncating to beginning only."""
        compressor = TokenLimitCompressor(max_tokens=50, preserve_end=False)
        result = await compressor.compress(LONG_TEXT)

        assert result.compressed_tokens <= 50
        assert result.compression_ratio < 1.0
        assert result.strategy == CompressionStrategy.TOKEN_LIMIT
        assert "[...]" not in result.compressed_text

    @pytest.mark.asyncio
    async def test_compress_long_text_with_end(self):
        """Test preserving beginning and end."""
        compressor = TokenLimitCompressor(
            max_tokens=50, preserve_end=True, end_ratio=0.3,
        )
        result = await compressor.compress(LONG_TEXT)

        assert result.compressed_tokens <= 60  # Approximate due to [...]
        assert "[...]" in result.compressed_text

    @pytest.mark.asyncio
    async def test_metadata(self):
        """Test metadata in result."""
        compressor = TokenLimitCompressor(
            max_tokens=100, preserve_end=True, end_ratio=0.25,
        )
        result = await compressor.compress(LONG_TEXT)

        assert result.metadata["max_tokens"] == 100
        assert result.metadata["preserve_end"] is True
        assert result.metadata["end_ratio"] == 0.25


# Tests for SemanticDeduplicationCompressor
class TestSemanticDeduplicationCompressor:
    """Tests for SemanticDeduplicationCompressor."""

    @pytest.mark.asyncio
    async def test_creation(self):
        """Test creating semantic dedup compressor."""
        compressor = SemanticDeduplicationCompressor(similarity_threshold=0.8)

        assert compressor.similarity_threshold == 0.8
        assert compressor.preserve_first is True

    @pytest.mark.asyncio
    async def test_compress_no_duplicates(self):
        """Test text without duplicates."""
        compressor = SemanticDeduplicationCompressor()
        text = "First sentence. Second sentence. Third sentence."

        result = await compressor.compress(text)

        # No duplicates removed, though minor token changes may occur
        assert result.metadata["removed_duplicates"] == 0
        assert result.compression_ratio >= 0.9  # Minimal compression

    @pytest.mark.asyncio
    async def test_compress_with_duplicates(self):
        """Test removing duplicate sentences."""
        compressor = SemanticDeduplicationCompressor(similarity_threshold=0.5)
        text = """
        Machine learning is a type of AI. Machine learning is a type of AI.
        Machine learning builds models. Machine learning constructs models.
        """

        result = await compressor.compress(text)

        # Should remove similar sentences with lower threshold
        assert result.metadata["removed_duplicates"] >= 1
        assert result.compressed_tokens <= result.original_tokens
        assert result.strategy == CompressionStrategy.SEMANTIC_DEDUP

    @pytest.mark.asyncio
    async def test_exact_duplicates(self):
        """Test removing exact duplicates."""
        compressor = SemanticDeduplicationCompressor(similarity_threshold=1.0)
        text = "Same sentence. Same sentence. Different sentence."

        result = await compressor.compress(text)

        # Should remove exact duplicate
        assert "Different sentence" in result.compressed_text
        assert result.metadata["removed_duplicates"] >= 1

    @pytest.mark.asyncio
    async def test_metadata(self):
        """Test metadata in result."""
        compressor = SemanticDeduplicationCompressor()
        result = await compressor.compress(SAMPLE_TEXT)

        assert "original_sentences" in result.metadata
        assert "unique_sentences" in result.metadata
        assert "removed_duplicates" in result.metadata
        assert "similarity_threshold" in result.metadata


# Tests for HybridCompressor
class TestHybridCompressor:
    """Tests for HybridCompressor."""

    @pytest.mark.asyncio
    async def test_creation(self):
        """Test creating hybrid compressor."""
        compressors = [
            SemanticDeduplicationCompressor(),
            TokenLimitCompressor(max_tokens=100),
        ]
        compressor = HybridCompressor(compressors=compressors)

        assert len(compressor.compressors) == 2

    @pytest.mark.asyncio
    async def test_compress_sequential(self):
        """Test sequential compression."""
        compressors = [
            SemanticDeduplicationCompressor(),
            ExtractiveSummaryCompressor(max_sentences=2),
            TokenLimitCompressor(max_tokens=50),
        ]
        compressor = HybridCompressor(compressors=compressors)

        result = await compressor.compress(LONG_TEXT)

        assert result.strategy == CompressionStrategy.HYBRID
        assert result.compressed_tokens < result.original_tokens
        assert len(result.metadata["intermediate_results"]) == 3

    @pytest.mark.asyncio
    async def test_metadata_tracking(self):
        """Test intermediate results tracking."""
        compressors = [
            TokenLimitCompressor(max_tokens=200),
            ExtractiveSummaryCompressor(max_sentences=3),
        ]
        compressor = HybridCompressor(compressors=compressors)

        result = await compressor.compress(LONG_TEXT)

        intermediate = result.metadata["intermediate_results"]
        assert len(intermediate) == 2
        assert intermediate[0]["compressor"] == "TokenLimitCompressor"
        assert intermediate[1]["compressor"] == "ExtractiveSummaryCompressor"
        assert "compression_ratio" in intermediate[0]
        assert "tokens" in intermediate[0]

    @pytest.mark.asyncio
    async def test_progressive_compression(self):
        """Test that compression increases with each step."""
        compressors = [
            SemanticDeduplicationCompressor(),
            ExtractiveSummaryCompressor(max_sentences=5),
            TokenLimitCompressor(max_tokens=100),
        ]
        compressor = HybridCompressor(compressors=compressors)

        result = await compressor.compress(LONG_TEXT)

        # Final compression should be best
        assert result.compression_ratio < 0.5  # At least 50% reduction


# Tests for convenience function
class TestConvenienceFunction:
    """Tests for compress_context convenience function."""

    @pytest.mark.asyncio
    async def test_extractive_strategy(self):
        """Test with extractive strategy."""
        result = await compress_context(
            SAMPLE_TEXT,
            strategy=CompressionStrategy.EXTRACTIVE,
            max_sentences=2,
        )

        assert result.strategy == CompressionStrategy.EXTRACTIVE
        assert result.compressed_tokens <= result.original_tokens

    @pytest.mark.asyncio
    async def test_abstractive_strategy(self):
        """Test with abstractive strategy."""
        llm = MockLLMClient()
        result = await compress_context(
            SAMPLE_TEXT,
            strategy=CompressionStrategy.ABSTRACTIVE,
            llm_client=llm,
            max_tokens=50,
        )

        assert result.strategy == CompressionStrategy.ABSTRACTIVE

    @pytest.mark.asyncio
    async def test_token_limit_strategy(self):
        """Test with token limit strategy."""
        result = await compress_context(
            LONG_TEXT,
            strategy=CompressionStrategy.TOKEN_LIMIT,
            max_tokens=100,
        )

        assert result.strategy == CompressionStrategy.TOKEN_LIMIT
        assert result.compressed_tokens <= 100

    @pytest.mark.asyncio
    async def test_semantic_dedup_strategy(self):
        """Test with semantic deduplication strategy."""
        result = await compress_context(
            SAMPLE_TEXT,
            strategy=CompressionStrategy.SEMANTIC_DEDUP,
            similarity_threshold=0.8,
        )

        assert result.strategy == CompressionStrategy.SEMANTIC_DEDUP

    @pytest.mark.asyncio
    async def test_hybrid_strategy(self):
        """Test with hybrid strategy."""
        compressors = [
            ExtractiveSummaryCompressor(max_sentences=3),
            TokenLimitCompressor(max_tokens=100),
        ]

        result = await compress_context(
            LONG_TEXT,
            strategy=CompressionStrategy.HYBRID,
            compressors=compressors,
        )

        assert result.strategy == CompressionStrategy.HYBRID

    @pytest.mark.asyncio
    async def test_invalid_strategy(self):
        """Test with invalid strategy."""
        with pytest.raises(ValueError, match="Unknown compression strategy"):
            await compress_context(SAMPLE_TEXT, strategy="invalid")

    @pytest.mark.asyncio
    async def test_missing_llm_client(self):
        """Test abstractive without LLM client."""
        with pytest.raises(ValueError, match="requires 'llm_client'"):
            await compress_context(
                SAMPLE_TEXT,
                strategy=CompressionStrategy.ABSTRACTIVE,
            )

    @pytest.mark.asyncio
    async def test_missing_compressors(self):
        """Test hybrid without compressors list."""
        with pytest.raises(ValueError, match="requires 'compressors'"):
            await compress_context(
                SAMPLE_TEXT,
                strategy=CompressionStrategy.HYBRID,
            )


# Integration tests
class TestIntegration:
    """Integration tests for context compression."""

    @pytest.mark.asyncio
    async def test_full_compression_pipeline(self):
        """Test complete compression workflow."""
        # Start with long text
        original_text = LONG_TEXT

        # Apply deduplication
        dedup = SemanticDeduplicationCompressor()
        result1 = await dedup.compress(original_text)

        # Apply extractive compression
        extractive = ExtractiveSummaryCompressor(max_sentences=5)
        result2 = await extractive.compress(result1.compressed_text)

        # Apply token limit
        token_limit = TokenLimitCompressor(max_tokens=100)
        result3 = await token_limit.compress(result2.compressed_text)

        # Verify progressive compression
        assert result1.compressed_tokens <= result1.original_tokens
        assert result2.compressed_tokens <= result1.compressed_tokens
        assert result3.compressed_tokens <= result2.compressed_tokens
        assert result3.compressed_tokens <= 100

    @pytest.mark.asyncio
    async def test_query_aware_compression(self):
        """Test query-aware compression."""
        query = "What is machine learning?"

        # Extractive with query
        extractive = ExtractiveSummaryCompressor(max_sentences=2)
        result = await extractive.compress(LONG_TEXT, query=query)

        # Should prioritize query-relevant content
        assert (
            "machine learning" in result.compressed_text.lower()
            or "learning" in result.compressed_text.lower()
        )

    @pytest.mark.asyncio
    async def test_compression_preserves_meaning(self):
        """Test that compression preserves key information."""
        text = """
        Python is a high-level programming language. Python emphasizes code readability.
        Python uses significant indentation. Python supports multiple programming paradigms.
        """

        compressor = ExtractiveSummaryCompressor(max_sentences=2)
        result = await compressor.compress(text, query="What is Python?")

        # Should keep key facts about Python
        assert "python" in result.compressed_text.lower()

    @pytest.mark.asyncio
    async def test_extreme_compression(self):
        """Test extreme compression ratios."""
        # Very aggressive hybrid compression
        compressors = [
            SemanticDeduplicationCompressor(similarity_threshold=0.6),
            ExtractiveSummaryCompressor(max_sentences=2),
            TokenLimitCompressor(max_tokens=30),
        ]
        hybrid = HybridCompressor(compressors=compressors)

        result = await hybrid.compress(LONG_TEXT)

        # Should achieve significant compression
        assert result.compression_ratio < 0.15  # Less than 15% of original
        assert result.savings_percentage > 85  # More than 85% savings
