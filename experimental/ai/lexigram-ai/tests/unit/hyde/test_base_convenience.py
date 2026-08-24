"""Tests for base HyDE generator functionality, convenience function, and integration."""

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.hyde import HyDEStrategy, SingleHyDEGenerator, generate_hyde
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


class TestBaseHyDEGenerator:
    """Tests for base HyDE generator functionality."""

    @pytest.mark.asyncio
    async def test_extract_content_variants(self):
        llm = MockLLM()
        generator = SingleHyDEGenerator(llm_client=llm)

        class ContentResponse:
            content = "Test content"

        content = generator._extract_content(ContentResponse())
        assert content == "Test content"

        content = generator._extract_content("Direct string")
        assert content == "Direct string"

    @pytest.mark.asyncio
    async def test_build_prompt_variants(self):
        llm = MockLLM()
        generator = SingleHyDEGenerator(llm_client=llm)

        prompt = generator._build_prompt("What is AI?")
        assert "What is AI?" in prompt

        prompt = generator._build_prompt("Query", context="Context here")
        assert "Context here" in prompt

        prompt = generator._build_prompt("Query", domain="Science")
        assert "Science" in prompt

    @pytest.mark.asyncio
    async def test_aggregate_embeddings(self):
        llm = MockLLM()
        generator = SingleHyDEGenerator(llm_client=llm)

        embeddings = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]

        aggregated = generator._aggregate_embeddings(embeddings)
        assert len(aggregated) == 3
        magnitude = sum(x * x for x in aggregated) ** 0.5
        assert magnitude == pytest.approx(1.0, abs=0.01)

        weights = [2.0, 1.0, 1.0]
        aggregated = generator._aggregate_embeddings(embeddings, weights)
        assert aggregated[0] > aggregated[1]


class TestConvenienceFunction:
    """Tests for generate_hyde convenience function."""

    @pytest.mark.asyncio
    async def test_single_strategy(self):
        llm = MockLLM()
        result = await generate_hyde(
            "Query",
            llm_client=llm,
            strategy=HyDEStrategy.SINGLE,
        )

        assert result.strategy == HyDEStrategy.SINGLE
        assert result.num_documents == 1

    @pytest.mark.asyncio
    async def test_multiple_strategy(self):
        llm = MockLLM()
        result = await generate_hyde(
            "Query",
            llm_client=llm,
            strategy=HyDEStrategy.MULTIPLE,
            num_documents=3,
        )

        assert result.strategy == HyDEStrategy.MULTIPLE
        assert result.num_documents == 3

    @pytest.mark.asyncio
    async def test_weighted_strategy(self):
        llm = MockLLM()
        embedding = MockEmbedding()
        result = await generate_hyde(
            "Query",
            llm_client=llm,
            embedding_client=embedding,
            strategy=HyDEStrategy.WEIGHTED,
            num_documents=2,
        )

        assert result.strategy == HyDEStrategy.WEIGHTED
        assert result.aggregated_embedding is not None

    @pytest.mark.asyncio
    async def test_reverse_strategy(self):
        response = """Passage: Test passage.
Related Queries:
1. Query 1
2. Query 2"""

        llm = MockLLM(responses=[response])
        result = await generate_hyde(
            "Query",
            llm_client=llm,
            strategy=HyDEStrategy.REVERSE,
        )

        assert result.strategy == HyDEStrategy.REVERSE
        assert "related_queries" in result.metadata

    @pytest.mark.asyncio
    async def test_invalid_strategy(self):
        llm = MockLLM()

        with pytest.raises(ValueError, match="Unknown HyDE strategy"):
            await generate_hyde(
                "Query",
                llm_client=llm,
                strategy="invalid",
            )

    @pytest.mark.asyncio
    async def test_weighted_without_embedding(self):
        llm = MockLLM()

        with pytest.raises(ValueError, match="requires embedding_client"):
            await generate_hyde(
                "Query",
                llm_client=llm,
                strategy=HyDEStrategy.WEIGHTED,
            )


class TestIntegration:
    """Integration tests for HyDE."""

    @pytest.mark.asyncio
    async def test_full_pipeline_single(self):
        llm = MockLLM(
            responses=[
                "Neural networks are computational models inspired by the brain.",
            ],
        )
        embedding = MockEmbedding()

        result = await generate_hyde(
            "What are neural networks?",
            llm_client=llm,
            embedding_client=embedding,
            strategy=HyDEStrategy.SINGLE,
        )

        assert result.num_documents == 1
        assert "neural" in result.hypothetical_docs[0].content.lower()
        assert result.aggregated_embedding is not None

    @pytest.mark.asyncio
    async def test_full_pipeline_multiple(self):
        responses = [
            "Deep learning uses neural networks.",
            "Deep learning excels at pattern recognition.",
            "Deep learning powers modern AI.",
        ]
        llm = MockLLM(responses=responses)
        embedding = MockEmbedding()

        result = await generate_hyde(
            "What is deep learning?",
            llm_client=llm,
            embedding_client=embedding,
            strategy=HyDEStrategy.MULTIPLE,
            num_documents=3,
        )

        assert result.num_documents == 3
        assert result.aggregated_embedding is not None
        assert result.avg_confidence < 1.0

    @pytest.mark.asyncio
    async def test_comparison_strategies(self):
        llm = MockLLM()
        embedding = MockEmbedding()

        query = "What is machine learning?"

        result_single = await generate_hyde(
            query,
            llm,
            embedding,
            HyDEStrategy.SINGLE,
        )

        result_multiple = await generate_hyde(
            query,
            llm,
            embedding,
            HyDEStrategy.MULTIPLE,
            num_documents=3,
        )

        result_weighted = await generate_hyde(
            query,
            llm,
            embedding,
            HyDEStrategy.WEIGHTED,
            num_documents=3,
        )

        assert result_single.num_documents == 1
        assert result_multiple.num_documents == 3
        assert result_weighted.num_documents == 3
        assert "weights" in result_weighted.metadata

    @pytest.mark.asyncio
    async def test_embedding_quality(self):
        llm = MockLLM()
        embedding = MockEmbedding()

        result = await generate_hyde(
            "Test query",
            llm_client=llm,
            embedding_client=embedding,
            strategy=HyDEStrategy.WEIGHTED,
            num_documents=2,
        )

        emb = result.aggregated_embedding
        magnitude = sum(x * x for x in emb) ** 0.5
        assert magnitude == pytest.approx(1.0, abs=0.01)
