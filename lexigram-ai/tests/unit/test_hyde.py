"""Tests for HyDE (Hypothetical Document Embeddings)."""

from __future__ import annotations

from enum import Enum

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.hyde import (
    HyDEResult,
    HyDEStrategy,
    HypotheticalDocument,
    MultipleHyDEGenerator,
    ReverseHyDEGenerator,
    SingleHyDEGenerator,
    WeightedHyDEGenerator,
    generate_hyde,
)


# Mock clients
class MockLLM:
    """Mock LLM client."""

    def __init__(self, responses=None):
        self.responses = responses or []
        self.call_count = 0

    async def complete(self, messages, temperature=0.7, max_tokens=None):
        """Return mock response."""
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return MockResponse(response)

        # Default response
        return MockResponse(
            "Machine learning is a branch of AI that enables systems to learn "
            "from data and improve performance without explicit programming.",
        )


class MockResponse:
    """Mock LLM response."""

    def __init__(self, content):
        self.content = content

    def is_err(self):
        return False

    def unwrap(self):
        return self

    def unwrap_err(self):
        raise AssertionError("MockResponse has no error")


class MockEmbedding:
    """Mock embedding client."""

    async def embed(self, texts):
        """Return mock embeddings."""
        # Return simple embeddings based on text length
        return list(map(lambda text: [float(len(text)) / 100, 0.5, 0.3], texts))


# Tests for data models
class TestDataModels:
    """Tests for HyDE data models."""

    def test_hypothetical_document_creation(self):
        """Test creating hypothetical document."""
        doc = HypotheticalDocument(
            content="Test content",
            query="test query",
            confidence=0.9,
        )

        assert doc.content == "Test content"
        assert doc.query == "test query"
        assert doc.confidence == 0.9
        assert "timestamp" in doc.__dict__

    def test_hypothetical_document_repr(self):
        """Test document representation."""
        doc = HypotheticalDocument(
            content="Test content here",
            query="query",
            confidence=0.85,
        )

        repr_str = repr(doc)
        assert "length=17" in repr_str
        assert "confidence=0.85" in repr_str

    def test_hyde_result_creation(self):
        """Test creating HyDE result."""
        doc = HypotheticalDocument(
            content="Test",
            query="query",
        )

        result = HyDEResult(
            query="query",
            hypothetical_docs=[doc],
            strategy=HyDEStrategy.SINGLE,
        )

        assert result.query == "query"
        assert result.num_documents == 1
        assert result.strategy == HyDEStrategy.SINGLE

    def test_hyde_result_properties(self):
        """Test HyDE result properties."""
        docs = [
            HypotheticalDocument("Doc 1", "query", confidence=1.0),
            HypotheticalDocument("Doc 2", "query", confidence=0.8),
            HypotheticalDocument("Doc 3", "query", confidence=0.6),
        ]

        result = HyDEResult(
            query="query",
            hypothetical_docs=docs,
            strategy=HyDEStrategy.MULTIPLE,
        )

        assert result.num_documents == 3
        assert result.avg_confidence == pytest.approx(0.8, abs=0.01)
        assert result.total_length == 15  # "Doc 1" (5) + "Doc 2" (5) + "Doc 3" (5)

    def test_hyde_result_empty(self):
        """Test HyDE result with no documents."""
        result = HyDEResult(
            query="query",
            hypothetical_docs=[],
            strategy=HyDEStrategy.SINGLE,
        )

        assert result.num_documents == 0
        assert result.avg_confidence == 0.0
        assert result.total_length == 0


# Tests for SingleHyDEGenerator
class TestSingleHyDEGenerator:
    """Tests for single HyDE generation."""

    @pytest.mark.asyncio
    async def test_creation(self):
        """Test creating single HyDE generator."""
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
        """Test generating single hypothetical document."""
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
        """Test generating with embeddings."""
        llm = MockLLM()
        embedding = MockEmbedding()
        generator = SingleHyDEGenerator(
            llm_client=llm,
            embedding_client=embedding,
        )

        result = await generator.generate("What is machine learning?")

        assert result.aggregated_embedding is not None
        assert len(result.aggregated_embedding) == 3  # Mock returns 3D vectors

    @pytest.mark.asyncio
    async def test_generate_with_context(self):
        """Test generating with additional context."""
        llm = MockLLM()
        generator = SingleHyDEGenerator(llm_client=llm)

        result = await generator.generate(
            "What is supervised learning?",
            context="Machine learning course",
            domain="Education",
        )

        assert result.num_documents == 1
        assert result.hypothetical_docs[0].metadata["temperature"] == 0.7


# Tests for MultipleHyDEGenerator
class TestMultipleHyDEGenerator:
    """Tests for multiple HyDE generation."""

    @pytest.mark.asyncio
    async def test_creation(self):
        """Test creating multiple HyDE generator."""
        llm = MockLLM()
        generator = MultipleHyDEGenerator(
            llm_client=llm,
            default_num_documents=5,
        )

        assert generator.default_num_documents == 5

    @pytest.mark.asyncio
    async def test_generate_multiple_documents(self):
        """Test generating multiple documents."""
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
        assert all(
            "data" in doc.content.lower() or "ml" in doc.content.lower()
            for doc in result.hypothetical_docs[:3]
        )

    @pytest.mark.asyncio
    async def test_confidence_decay(self):
        """Test confidence decreases for later documents."""
        llm = MockLLM()
        generator = MultipleHyDEGenerator(llm_client=llm)

        result = await generator.generate("Query", num_documents=3)

        confidences = list(map(lambda doc: doc.confidence, result.hypothetical_docs))
        # First doc should have highest confidence
        assert confidences[0] > confidences[1] > confidences[2]

    @pytest.mark.asyncio
    async def test_generate_with_embedding_aggregation(self):
        """Test embedding aggregation with multiple docs."""
        llm = MockLLM()
        embedding = MockEmbedding()
        generator = MultipleHyDEGenerator(
            llm_client=llm,
            embedding_client=embedding,
        )

        result = await generator.generate("Query", num_documents=3)

        assert result.aggregated_embedding is not None
        # Should be normalized
        magnitude = sum(x * x for x in result.aggregated_embedding) ** 0.5
        assert magnitude == pytest.approx(1.0, abs=0.01)


# Tests for WeightedHyDEGenerator
class TestWeightedHyDEGenerator:
    """Tests for weighted HyDE generation."""

    @pytest.mark.asyncio
    async def test_creation(self):
        """Test creating weighted HyDE generator."""
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
        """Test weighted generation."""
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
        """Test exponential confidence decay."""
        llm = MockLLM()
        embedding = MockEmbedding()
        generator = WeightedHyDEGenerator(
            llm_client=llm,
            embedding_client=embedding,
            confidence_decay=0.5,
        )

        result = await generator.generate("Query", num_documents=4)

        confidences = list(map(lambda doc: doc.confidence, result.hypothetical_docs))
        # Should follow exponential decay: 1.0, 0.5, 0.25, 0.125
        assert confidences[0] == pytest.approx(1.0)
        assert confidences[1] == pytest.approx(0.5)
        assert confidences[2] == pytest.approx(0.25)
        assert confidences[3] == pytest.approx(0.125)

    @pytest.mark.asyncio
    async def test_weighted_aggregation(self):
        """Test that weights affect aggregation."""
        llm = MockLLM()
        embedding = MockEmbedding()
        generator = WeightedHyDEGenerator(
            llm_client=llm,
            embedding_client=embedding,
        )

        result = await generator.generate("Query", num_documents=2)

        weights = result.metadata["weights"]
        # First doc should have higher weight
        assert weights[0] > weights[1]


# Tests for ReverseHyDEGenerator
class TestReverseHyDEGenerator:
    """Tests for reverse HyDE generation."""

    @pytest.mark.asyncio
    async def test_creation(self):
        """Test creating reverse HyDE generator."""
        llm = MockLLM()
        generator = ReverseHyDEGenerator(llm_client=llm)

        assert generator.temperature == 0.5  # Lower for precise queries

    @pytest.mark.asyncio
    async def test_generate_reverse(self):
        """Test reverse generation."""
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
        """Test parsing reverse HyDE response."""
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


# Tests for base generator
class TestBaseHyDEGenerator:
    """Tests for base HyDE generator functionality."""

    @pytest.mark.asyncio
    async def test_extract_content_variants(self):
        """Test extracting content from different response formats."""
        llm = MockLLM()
        generator = SingleHyDEGenerator(llm_client=llm)

        # Test with .content
        class ContentResponse:
            content = "Test content"

        content = generator._extract_content(ContentResponse())
        assert content == "Test content"

        # Test with string
        content = generator._extract_content("Direct string")
        assert content == "Direct string"

    @pytest.mark.asyncio
    async def test_build_prompt_variants(self):
        """Test prompt building with different parameters."""
        llm = MockLLM()
        generator = SingleHyDEGenerator(llm_client=llm)

        # Basic prompt
        prompt = generator._build_prompt("What is AI?")
        assert "What is AI?" in prompt

        # With context
        prompt = generator._build_prompt("Query", context="Context here")
        assert "Context here" in prompt

        # With domain
        prompt = generator._build_prompt("Query", domain="Science")
        assert "Science" in prompt

    @pytest.mark.asyncio
    async def test_aggregate_embeddings(self):
        """Test embedding aggregation."""
        llm = MockLLM()
        generator = SingleHyDEGenerator(llm_client=llm)

        embeddings = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]

        # Equal weights
        aggregated = generator._aggregate_embeddings(embeddings)
        assert len(aggregated) == 3
        # Should be normalized
        magnitude = sum(x * x for x in aggregated) ** 0.5
        assert magnitude == pytest.approx(1.0, abs=0.01)

        # Custom weights
        weights = [2.0, 1.0, 1.0]
        aggregated = generator._aggregate_embeddings(embeddings, weights)
        # First dimension should have higher value
        assert aggregated[0] > aggregated[1]


# Tests for convenience function
class TestConvenienceFunction:
    """Tests for generate_hyde convenience function."""

    @pytest.mark.asyncio
    async def test_single_strategy(self):
        """Test with single strategy."""
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
        """Test with multiple strategy."""
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
        """Test with weighted strategy."""
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
        """Test with reverse strategy."""
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
        """Test with invalid strategy."""
        llm = MockLLM()

        with pytest.raises(ValueError, match="Unknown HyDE strategy"):
            await generate_hyde(
                "Query",
                llm_client=llm,
                strategy="invalid",
            )

    @pytest.mark.asyncio
    async def test_weighted_without_embedding(self):
        """Test weighted strategy without embedding client."""
        llm = MockLLM()

        with pytest.raises(ValueError, match="requires embedding_client"):
            await generate_hyde(
                "Query",
                llm_client=llm,
                strategy=HyDEStrategy.WEIGHTED,
            )


# Integration tests
class TestIntegration:
    """Integration tests for HyDE."""

    @pytest.mark.asyncio
    async def test_full_pipeline_single(self):
        """Test full pipeline with single HyDE."""
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
        """Test full pipeline with multiple HyDE."""
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
        assert result.avg_confidence < 1.0  # Due to confidence decay

    @pytest.mark.asyncio
    async def test_comparison_strategies(self):
        """Test comparing different strategies."""
        llm = MockLLM()
        embedding = MockEmbedding()

        query = "What is machine learning?"

        # Single
        result_single = await generate_hyde(
            query,
            llm,
            embedding,
            HyDEStrategy.SINGLE,
        )

        # Multiple
        result_multiple = await generate_hyde(
            query,
            llm,
            embedding,
            HyDEStrategy.MULTIPLE,
            num_documents=3,
        )

        # Weighted
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
        """Test that embeddings are properly normalized."""
        llm = MockLLM()
        embedding = MockEmbedding()

        result = await generate_hyde(
            "Test query",
            llm_client=llm,
            embedding_client=embedding,
            strategy=HyDEStrategy.WEIGHTED,
            num_documents=2,
        )

        # Check normalization
        emb = result.aggregated_embedding
        magnitude = sum(x * x for x in emb) ** 0.5
        assert magnitude == pytest.approx(1.0, abs=0.01)
