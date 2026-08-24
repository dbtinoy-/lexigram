"""Tests for Single and Multiple HyDE generators."""

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.hyde import (
    HyDEStrategy,
    MultipleHyDEGenerator,
    SingleHyDEGenerator,
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


class TestSingleHyDEGenerator:
    """Tests for single HyDE generation."""

    @pytest.mark.asyncio
    async def test_creation(self):
        llm = MockLLM()
        generator = SingleHyDEGenerator(
            llm_client=llm,
            temperature=0.7,
            max_tokens=200,
        )

        assert generator.temperature == 0.7
        assert generator.max_tokens == 200

    @pytest.mark.asyncio
    async def test_generate_single_document(self):
        llm = MockLLM(
            responses=["AI enables machines to perform intelligent tasks."],
        )
        generator = SingleHyDEGenerator(llm_client=llm)

        result = await generator.generate("What is AI?")

        assert result.strategy == HyDEStrategy.SINGLE
        assert result.num_documents == 1
        assert result.query == "What is AI?"
        assert "intelligent" in result.hypothetical_docs[0].content.lower()

    @pytest.mark.asyncio
    async def test_generate_with_embedding(self):
        llm = MockLLM()
        embedding = MockEmbedding()
        generator = SingleHyDEGenerator(
            llm_client=llm,
            embedding_client=embedding,
        )

        result = await generator.generate("What is machine learning?")

        assert result.aggregated_embedding is not None
        assert len(result.aggregated_embedding) == 3

    @pytest.mark.asyncio
    async def test_generate_with_context(self):
        llm = MockLLM()
        generator = SingleHyDEGenerator(llm_client=llm)

        result = await generator.generate(
            "What is supervised learning?",
            context="Machine learning course",
            domain="Education",
        )

        assert result.num_documents == 1
        assert result.hypothetical_docs[0].metadata["temperature"] == 0.7


class TestMultipleHyDEGenerator:
    """Tests for multiple HyDE generation."""

    @pytest.mark.asyncio
    async def test_creation(self):
        llm = MockLLM()
        generator = MultipleHyDEGenerator(
            llm_client=llm,
            default_num_documents=5,
        )

        assert generator.default_num_documents == 5

    @pytest.mark.asyncio
    async def test_generate_multiple_documents(self):
        responses = [
            "ML learns from data patterns.",
            "ML algorithms improve with experience.",
            "ML enables predictive analytics.",
        ]
        llm = MockLLM(responses=responses)
        generator = MultipleHyDEGenerator(llm_client=llm)

        result = await generator.generate("What is ML?", num_documents=3)

        assert result.strategy == HyDEStrategy.MULTIPLE
        assert result.num_documents == 3

    @pytest.mark.asyncio
    async def test_confidence_decay(self):
        llm = MockLLM()
        generator = MultipleHyDEGenerator(llm_client=llm)

        result = await generator.generate("Query", num_documents=3)

        confidences = list(map(lambda doc: doc.confidence, result.hypothetical_docs))
        assert confidences[0] > confidences[1] > confidences[2]

    @pytest.mark.asyncio
    async def test_generate_with_embedding_aggregation(self):
        llm = MockLLM()
        embedding = MockEmbedding()
        generator = MultipleHyDEGenerator(
            llm_client=llm,
            embedding_client=embedding,
        )

        result = await generator.generate("Query", num_documents=3)

        assert result.aggregated_embedding is not None
        magnitude = sum(x * x for x in result.aggregated_embedding) ** 0.5
        assert magnitude == pytest.approx(1.0, abs=0.01)
