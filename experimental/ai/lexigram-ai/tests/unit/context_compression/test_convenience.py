"""Tests for compress_context convenience function."""

from __future__ import annotations

import pytest

try:
    from lexigram.ai.rag.context_compression import (
        CompressionStrategy,
        ExtractiveSummaryCompressor,
        SemanticDeduplicationCompressor,
        TokenLimitCompressor,
        compress_context,
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


class MockLLMClient:
    def __init__(self, responses=None):
        self.responses = responses or []
        self.call_count = 0

    async def complete(self, messages, temperature=0.7, max_tokens=None):
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return MockResponse(response)
        return MockResponse("This is a concise summary of the main points.")


class MockResponse:
    def __init__(self, content):
        self.content = content

    def is_err(self):
        return False

    def unwrap(self):
        return self

    def unwrap_err(self):
        raise AssertionError("MockResponse has no error")


class TestConvenienceFunction:
    """Tests for compress_context convenience function."""

    @pytest.mark.asyncio
    async def test_extractive_strategy(self):
        result = await compress_context(
            SAMPLE_TEXT,
            strategy=CompressionStrategy.EXTRACTIVE,
            max_sentences=2,
        )

        assert result.strategy == CompressionStrategy.EXTRACTIVE
        assert result.compressed_tokens <= result.original_tokens

    @pytest.mark.asyncio
    async def test_abstractive_strategy(self):
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
        result = await compress_context(
            LONG_TEXT,
            strategy=CompressionStrategy.TOKEN_LIMIT,
            max_tokens=100,
        )

        assert result.strategy == CompressionStrategy.TOKEN_LIMIT
        assert result.compressed_tokens <= 100

    @pytest.mark.asyncio
    async def test_semantic_dedup_strategy(self):
        result = await compress_context(
            SAMPLE_TEXT,
            strategy=CompressionStrategy.SEMANTIC_DEDUP,
            similarity_threshold=0.8,
        )

        assert result.strategy == CompressionStrategy.SEMANTIC_DEDUP

    @pytest.mark.asyncio
    async def test_hybrid_strategy(self):
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
        with pytest.raises(ValueError, match="Unknown compression strategy"):
            await compress_context(SAMPLE_TEXT, strategy="invalid")

    @pytest.mark.asyncio
    async def test_missing_llm_client(self):
        with pytest.raises(ValueError, match="requires 'llm_client'"):
            await compress_context(
                SAMPLE_TEXT,
                strategy=CompressionStrategy.ABSTRACTIVE,
            )

    @pytest.mark.asyncio
    async def test_missing_compressors(self):
        with pytest.raises(ValueError, match="requires 'compressors'"):
            await compress_context(
                SAMPLE_TEXT,
                strategy=CompressionStrategy.HYBRID,
            )
