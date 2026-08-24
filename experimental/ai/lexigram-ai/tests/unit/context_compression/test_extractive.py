"""Tests for ExtractiveSummaryCompressor."""

from __future__ import annotations

import pytest

try:
    from lexigram.ai.rag.context_compression import (
        CompressionStrategy,
        ExtractiveSummaryCompressor,
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


class TestExtractiveSummaryCompressor:
    """Tests for ExtractiveSummaryCompressor."""

    @pytest.mark.asyncio
    async def test_creation(self):
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
        compressor = ExtractiveSummaryCompressor(max_sentences=10)
        result = await compressor.compress("Short text. Very short.")

        assert result.original_text == result.compressed_text
        assert result.compression_ratio == 1.0

    @pytest.mark.asyncio
    async def test_compress_long_text(self):
        compressor = ExtractiveSummaryCompressor(max_sentences=2)
        result = await compressor.compress(SAMPLE_TEXT)

        assert result.compressed_tokens < result.original_tokens
        assert result.compression_ratio < 1.0
        assert result.strategy == CompressionStrategy.EXTRACTIVE

    @pytest.mark.asyncio
    async def test_compress_with_query(self):
        compressor = ExtractiveSummaryCompressor(max_sentences=2)
        result = await compressor.compress(
            SAMPLE_TEXT,
            query="What are common applications?",
        )

        assert "applications" in result.compressed_text.lower()
        assert result.metadata["query_used"] is True

    @pytest.mark.asyncio
    async def test_compress_list_context(self):
        compressor = ExtractiveSummaryCompressor(max_sentences=2)
        context = ["First text here.", "Second text here.", "Third text here."]

        result = await compressor.compress(context)

        assert (
            result.original_text
            == "First text here.\n\nSecond text here.\n\nThird text here."
        )
        assert len(result.compressed_text) <= len(result.original_text)

    @pytest.mark.asyncio
    async def test_metadata(self):
        compressor = ExtractiveSummaryCompressor(max_sentences=2)
        result = await compressor.compress(SAMPLE_TEXT)

        assert "total_sentences" in result.metadata
        assert "selected_sentences" in result.metadata
        assert "timestamp" in result.metadata
