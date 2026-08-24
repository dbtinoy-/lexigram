"""Tests for SemanticDeduplicationCompressor."""

from __future__ import annotations

import pytest

try:
    from lexigram.ai.rag.context_compression import (
        CompressionStrategy,
        SemanticDeduplicationCompressor,
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


class TestSemanticDeduplicationCompressor:
    """Tests for SemanticDeduplicationCompressor."""

    @pytest.mark.asyncio
    async def test_creation(self):
        compressor = SemanticDeduplicationCompressor(similarity_threshold=0.8)

        assert compressor.similarity_threshold == 0.8
        assert compressor.preserve_first is True

    @pytest.mark.asyncio
    async def test_compress_no_duplicates(self):
        compressor = SemanticDeduplicationCompressor()
        text = "First sentence. Second sentence. Third sentence."

        result = await compressor.compress(text)

        assert result.metadata["removed_duplicates"] == 0
        assert result.compression_ratio >= 0.9

    @pytest.mark.asyncio
    async def test_compress_with_duplicates(self):
        compressor = SemanticDeduplicationCompressor(similarity_threshold=0.5)
        text = """
        Machine learning is a type of AI. Machine learning is a type of AI.
        Machine learning builds models. Machine learning constructs models.
        """

        result = await compressor.compress(text)

        assert result.metadata["removed_duplicates"] >= 1
        assert result.compressed_tokens <= result.original_tokens
        assert result.strategy == CompressionStrategy.SEMANTIC_DEDUP

    @pytest.mark.asyncio
    async def test_exact_duplicates(self):
        compressor = SemanticDeduplicationCompressor(similarity_threshold=1.0)
        text = "Same sentence. Same sentence. Different sentence."

        result = await compressor.compress(text)

        assert "Different sentence" in result.compressed_text
        assert result.metadata["removed_duplicates"] >= 1

    @pytest.mark.asyncio
    async def test_metadata(self):
        compressor = SemanticDeduplicationCompressor()
        result = await compressor.compress(SAMPLE_TEXT)

        assert "original_sentences" in result.metadata
        assert "unique_sentences" in result.metadata
        assert "removed_duplicates" in result.metadata
        assert "similarity_threshold" in result.metadata
