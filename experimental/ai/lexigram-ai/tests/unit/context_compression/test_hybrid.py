"""Tests for HybridCompressor."""

from __future__ import annotations

import pytest

try:
    from lexigram.ai.rag.context_compression import (
        CompressionStrategy,
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


class TestHybridCompressor:
    """Tests for HybridCompressor."""

    @pytest.mark.asyncio
    async def test_creation(self):
        compressors = [
            SemanticDeduplicationCompressor(),
            TokenLimitCompressor(max_tokens=100),
        ]
        compressor = HybridCompressor(compressors=compressors)

        assert len(compressor.compressors) == 2

    @pytest.mark.asyncio
    async def test_compress_sequential(self):
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
        compressors = [
            SemanticDeduplicationCompressor(),
            ExtractiveSummaryCompressor(max_sentences=5),
            TokenLimitCompressor(max_tokens=100),
        ]
        compressor = HybridCompressor(compressors=compressors)

        result = await compressor.compress(LONG_TEXT)

        assert result.compression_ratio < 0.5
