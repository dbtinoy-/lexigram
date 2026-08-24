"""Tests for AbstractiveCompressor."""

from __future__ import annotations

import pytest

try:
    from lexigram.ai.rag.context_compression import (
        AbstractiveCompressor,
        CompressionStrategy,
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


class TestAbstractiveCompressor:
    """Tests for AbstractiveCompressor."""

    @pytest.mark.asyncio
    async def test_creation(self):
        llm = MockLLMClient()
        compressor = AbstractiveCompressor(llm_client=llm, max_tokens=100)

        assert compressor.max_tokens == 100
        assert compressor.temperature == 0.3

    @pytest.mark.asyncio
    async def test_compress(self):
        llm = MockLLMClient(responses=["AI is machine intelligence for automation."])
        compressor = AbstractiveCompressor(llm_client=llm, max_tokens=50)

        result = await compressor.compress(LONG_TEXT)

        assert result.strategy == CompressionStrategy.ABSTRACTIVE
        assert result.compressed_text == "AI is machine intelligence for automation."
        assert llm.call_count == 1

    @pytest.mark.asyncio
    async def test_compress_with_query(self):
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
        llm = MockLLMClient()
        compressor = AbstractiveCompressor(
            llm_client=llm, max_tokens=100, temperature=0.5,
        )

        result = await compressor.compress(SAMPLE_TEXT)

        assert result.metadata["max_tokens"] == 100
        assert result.metadata["temperature"] == 0.5
        assert "timestamp" in result.metadata
