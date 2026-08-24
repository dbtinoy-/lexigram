"""Tests for TokenLimitCompressor."""

from __future__ import annotations

import pytest

try:
    from lexigram.ai.rag.context_compression import (
        CompressionStrategy,
        TokenLimitCompressor,
    )
except ImportError as e:
    pytest.skip(f"context_compression import failed: {e}", allow_module_level=True)

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


class TestTokenLimitCompressor:
    """Tests for TokenLimitCompressor."""

    @pytest.mark.asyncio
    async def test_creation(self):
        compressor = TokenLimitCompressor(max_tokens=500, preserve_end=True)

        assert compressor.max_tokens == 500
        assert compressor.preserve_end is True

    @pytest.mark.asyncio
    async def test_compress_short_text(self):
        compressor = TokenLimitCompressor(max_tokens=1000)
        result = await compressor.compress(SAMPLE_TEXT)

        assert result.compressed_text == result.original_text
        assert result.compression_ratio == 1.0

    @pytest.mark.asyncio
    async def test_compress_long_text_beginning_only(self):
        compressor = TokenLimitCompressor(max_tokens=50, preserve_end=False)
        result = await compressor.compress(LONG_TEXT)

        assert result.compressed_tokens <= 50
        assert result.compression_ratio < 1.0
        assert result.strategy == CompressionStrategy.TOKEN_LIMIT
        assert "[...]" not in result.compressed_text

    @pytest.mark.asyncio
    async def test_compress_long_text_with_end(self):
        compressor = TokenLimitCompressor(
            max_tokens=50, preserve_end=True, end_ratio=0.3,
        )
        result = await compressor.compress(LONG_TEXT)

        assert result.compressed_tokens <= 60
        assert "[...]" in result.compressed_text

    @pytest.mark.asyncio
    async def test_metadata(self):
        compressor = TokenLimitCompressor(
            max_tokens=100, preserve_end=True, end_ratio=0.25,
        )
        result = await compressor.compress(LONG_TEXT)

        assert result.metadata["max_tokens"] == 100
        assert result.metadata["preserve_end"] is True
        assert result.metadata["end_ratio"] == 0.25
