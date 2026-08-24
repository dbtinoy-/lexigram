"""Integration tests for context compression."""

from __future__ import annotations

import pytest

try:
    from lexigram.ai.rag.context_compression import (
        ExtractiveSummaryCompressor,
        HybridCompressor,
        SemanticDeduplicationCompressor,
        TokenLimitCompressor,
    )
except ImportError as e:
    pytest.skip(f"context_compression import failed: {e}", allow_module_level=True)

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


class TestIntegration:
    """Integration tests for context compression."""

    @pytest.mark.asyncio
    async def test_full_compression_pipeline(self):
        original_text = LONG_TEXT

        dedup = SemanticDeduplicationCompressor()
        result1 = await dedup.compress(original_text)

        extractive = ExtractiveSummaryCompressor(max_sentences=5)
        result2 = await extractive.compress(result1.compressed_text)

        token_limit = TokenLimitCompressor(max_tokens=100)
        result3 = await token_limit.compress(result2.compressed_text)

        assert result1.compressed_tokens <= result1.original_tokens
        assert result2.compressed_tokens <= result1.compressed_tokens
        assert result3.compressed_tokens <= result2.compressed_tokens
        assert result3.compressed_tokens <= 100

    @pytest.mark.asyncio
    async def test_query_aware_compression(self):
        query = "What is machine learning?"

        extractive = ExtractiveSummaryCompressor(max_sentences=2)
        result = await extractive.compress(LONG_TEXT, query=query)

        assert (
            "machine learning" in result.compressed_text.lower()
            or "learning" in result.compressed_text.lower()
        )

    @pytest.mark.asyncio
    async def test_compression_preserves_meaning(self):
        text = """
        Python is a high-level programming language. Python emphasizes code readability.
        Python uses significant indentation. Python supports multiple programming paradigms.
        """

        compressor = ExtractiveSummaryCompressor(max_sentences=2)
        result = await compressor.compress(text, query="What is Python?")

        assert "python" in result.compressed_text.lower()

    @pytest.mark.asyncio
    async def test_extreme_compression(self):
        compressors = [
            SemanticDeduplicationCompressor(similarity_threshold=0.6),
            ExtractiveSummaryCompressor(max_sentences=2),
            TokenLimitCompressor(max_tokens=30),
        ]
        hybrid = HybridCompressor(compressors=compressors)

        result = await hybrid.compress(LONG_TEXT)

        assert result.compression_ratio < 0.15
        assert result.savings_percentage > 85
