"""Tests for Weighted and Reverse HyDE generators."""

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.hyde import (
    HyDEStrategy,
    ReverseHyDEGenerator,
    WeightedHyDEGenerator,
)
class MockLLM:
    def __init__(self, responses=None):
        self.responses = responses or []
        self.call_count = 0

    async def complete(self, messages, temperature=0.7, max_tokens=None):
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return MockResponse(response)
        return MockResponse("Machine learning is a branch of AI.")


class MockResponse:
    def __init__(self, content):
        self.content = content
    def is_err(self):
        return False
    def unwrap(self):
        return self
    def unwrap_err(self):
        raise AssertionError("MockResponse has no error")


class MockEmbedding:
    async def embed(self, texts):
        return list(map(lambda text: [float(len(text)) / 100, 0.5, 0.3], texts))


class TestWeightedHyDEGenerator:
    """Tests for weighted HyDE generation."""

    @pytest.mark.asyncio
    async def test_creation(self):
        llm = MockLLM()
        embedding = MockEmbedding()
        generator = WeightedHyDEGenerator(
            llm_client=llm,
            embedding_client=embedding,
            confidence_decay=0.8,
        )

        assert generator.confidence_decay == 0.8

    @pytest.mark.asyncio
    async def test_generate_weighted(self):
        llm = MockLLM()
        embedding = MockEmbedding()
        generator = WeightedHyDEGenerator(
            llm_client=llm,
            embedding_client=embedding,
            confidence_decay=0.7,
        )

        result = await generator.generate("Query", num_documents=3)

        assert result.strategy == HyDEStrategy.WEIGHTED
        assert result.aggregated_embedding is not None
        assert "weights" in result.metadata

    @pytest.mark.asyncio
    async def test_exponential_decay(self):
        llm = MockLLM()
        embedding = MockEmbedding()
        generator = WeightedHyDEGenerator(
            llm_client=llm,
            embedding_client=embedding,
            confidence_decay=0.5,
        )

        result = await generator.generate("Query", num_documents=4)

        confidences = list(map(lambda doc: doc.confidence, result.hypothetical_docs))
        assert confidences[0] == pytest.approx(1.0)
        assert confidences[1] == pytest.approx(0.5)
        assert confidences[2] == pytest.approx(0.25)
        assert confidences[3] == pytest.approx(0.125)

    @pytest.mark.asyncio
    async def test_weighted_aggregation(self):
        llm = MockLLM()
        embedding = MockEmbedding()
        generator = WeightedHyDEGenerator(
            llm_client=llm,
            embedding_client=embedding,
        )

        result = await generator.generate("Query", num_documents=2)

        weights = result.metadata["weights"]
        assert weights[0] > weights[1]


class TestReverseHyDEGenerator:
    """Tests for reverse HyDE generation."""

    @pytest.mark.asyncio
    async def test_creation(self):
        llm = MockLLM()
        generator = ReverseHyDEGenerator(llm_client=llm)

        assert generator.temperature == 0.5

    @pytest.mark.asyncio
    async def test_generate_reverse(self):
        response = """Passage: Machine learning algorithms learn patterns from data to make predictions.
Related Queries:
1. How does machine learning work?
2. What are ML algorithms?
3. Can ML make predictions?"""

        llm = MockLLM(responses=[response])
        generator = ReverseHyDEGenerator(llm_client=llm)

        result = await generator.generate("What is ML?")

        assert result.strategy == HyDEStrategy.REVERSE
        assert result.num_documents == 1
        assert "related_queries" in result.metadata
        assert len(result.metadata["related_queries"]) == 3

    @pytest.mark.asyncio
    async def test_parse_reverse_response(self):
        response = """Passage: AI enables intelligent automation.
Related Queries:
1. What is AI?
2. How does AI work?
3. What are AI applications?"""

        llm = MockLLM(responses=[response])
        generator = ReverseHyDEGenerator(llm_client=llm)

        result = await generator.generate("AI query")

        passage = result.hypothetical_docs[0].content
        queries = result.metadata["related_queries"]

        assert "AI" in passage
        assert "intelligent" in passage
        assert len(queries) == 3
        assert "What is AI?" in queries
