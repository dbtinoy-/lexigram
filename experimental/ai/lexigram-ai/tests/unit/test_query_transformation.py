"""Tests for query transformation strategies."""

from __future__ import annotations

from enum import Enum

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.query import (
    CustomQueryTransformer,
    HyDEGenerator,
    MultiQueryGenerator,
    QueryExpander,
    QueryRewriter,
    TransformationPipeline,
    TransformationStrategy,
    TransformedQuery,
    create_transformer,
)


# Mock LLM Client for testing
class _OkResult:
    """Minimal Result-like success wrapper for tests."""

    def __init__(self, value):
        self._value = value

    def is_err(self):
        return False

    def unwrap(self):
        return self._value

    def unwrap_err(self):
        raise AssertionError("_OkResult has no error")


class MockLLMClient:
    """Mock LLM client for testing."""

    def __init__(self, responses=None):
        """Initialize with predefined responses."""
        self.responses = responses or []
        self.call_count = 0

    async def complete(self, messages, temperature=0.7, max_tokens=None):
        """Return predefined response."""
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return _OkResult(response)
        return _OkResult("default response")


class TestTransformedQuery:
    """Test TransformedQuery dataclass."""

    def test_creation(self):
        """Test creating TransformedQuery."""
        tq = TransformedQuery(
            original="test query",
            transformed=["query 1", "query 2"],
            strategy=TransformationStrategy.EXPANSION,
        )

        assert tq.original == "test query"
        assert len(tq.transformed) == 2
        assert tq.strategy == TransformationStrategy.EXPANSION

    def test_length(self):
        """Test __len__ method."""
        tq = TransformedQuery(
            original="test",
            transformed=["a", "b", "c"],
            strategy=TransformationStrategy.EXPANSION,
        )

        assert len(tq) == 3

    def test_iteration(self):
        """Test __iter__ method."""
        queries = ["a", "b", "c"]
        tq = TransformedQuery(
            original="test",
            transformed=queries,
            strategy=TransformationStrategy.EXPANSION,
        )

        assert list(tq) == queries

    def test_metadata(self):
        """Test metadata handling."""
        tq = TransformedQuery(
            original="test",
            transformed=["a"],
            strategy=TransformationStrategy.EXPANSION,
            metadata={"key": "value"},
        )

        assert tq.metadata["key"] == "value"


class TestQueryExpander:
    """Test QueryExpander."""

    @pytest.mark.asyncio
    async def test_predefined_expansion(self):
        """Test expansion with predefined terms."""
        expander = QueryExpander(
            expansion_terms={
                "ML": ["machine learning", "artificial intelligence"],
                "RAG": ["retrieval augmented generation"],
            },
        )

        result = await expander.transform("ML techniques")

        assert result.original == "ML techniques"
        assert "ML techniques" in result.transformed  # Original included
        assert "machine learning techniques" in result.transformed
        assert result.strategy == TransformationStrategy.EXPANSION

    @pytest.mark.asyncio
    async def test_no_expansion_terms(self):
        """Test with no matching expansion terms."""
        expander = QueryExpander(
            expansion_terms={"ML": ["machine learning"]},
        )

        result = await expander.transform("neural networks")

        assert len(result.transformed) == 1
        assert result.transformed[0] == "neural networks"

    @pytest.mark.asyncio
    async def test_exclude_original(self):
        """Test excluding original query."""
        expander = QueryExpander(
            expansion_terms={"ML": ["machine learning"]},
            include_original=False,
        )

        result = await expander.transform("ML basics")

        assert "ML basics" not in result.transformed
        assert "machine learning basics" in result.transformed

    @pytest.mark.asyncio
    async def test_max_expansions(self):
        """Test max_expansions limit."""
        expander = QueryExpander(
            expansion_terms={
                "test": ["a", "b", "c", "d", "e", "f"],
            },
            max_expansions=3,
        )

        result = await expander.transform("test query")

        # Original + max 3 expansions
        assert len(result.transformed) <= 4

    @pytest.mark.asyncio
    async def test_llm_expansion(self):
        """Test LLM-based expansion."""
        mock_client = MockLLMClient(
            responses=[
                "1. machine learning algorithms\n2. ML models\n3. AI techniques",
            ],
        )

        expander = QueryExpander(
            llm_client=mock_client,
            max_expansions=3,
        )

        result = await expander.transform("ML methods")

        assert len(result.transformed) >= 2
        assert "ML methods" in result.transformed

    @pytest.mark.asyncio
    async def test_strategy_property(self):
        """Test strategy property."""
        expander = QueryExpander()
        assert expander.strategy == TransformationStrategy.EXPANSION


class TestMultiQueryGenerator:
    """Test MultiQueryGenerator."""

    @pytest.mark.asyncio
    async def test_generate_multiple_queries(self):
        """Test generating multiple query variations."""
        mock_client = MockLLMClient(
            responses=[
                "1. What is retrieval augmented generation?\n"
                "2. Explain RAG systems\n"
                "3. How does RAG work?",
            ],
        )

        generator = MultiQueryGenerator(
            llm_client=mock_client,
            num_queries=3,
        )

        result = await generator.transform("What is RAG?")

        assert result.original == "What is RAG?"
        assert len(result.transformed) >= 2
        assert "What is RAG?" in result.transformed  # Original included

    @pytest.mark.asyncio
    async def test_exclude_original(self):
        """Test excluding original query."""
        mock_client = MockLLMClient(
            responses=["Query 1\nQuery 2\nQuery 3"],
        )

        generator = MultiQueryGenerator(
            llm_client=mock_client,
            num_queries=3,
            include_original=False,
        )

        result = await generator.transform("test")

        assert "test" not in result.transformed

    @pytest.mark.asyncio
    async def test_custom_temperature(self):
        """Test custom temperature setting."""
        mock_client = MockLLMClient(responses=["Query 1\nQuery 2"])

        generator = MultiQueryGenerator(
            llm_client=mock_client,
            num_queries=2,
            temperature=1.0,
        )

        result = await generator.transform("test")

        assert result.metadata["temperature"] == 1.0

    @pytest.mark.asyncio
    async def test_generation_failure_fallback(self):
        """Test fallback when generation fails."""

        # Client that raises exception
        class FailingClient:
            async def complete(self, messages, temperature=0.7, max_tokens=None):
                raise ConnectionError("Generation failed")

        generator = MultiQueryGenerator(
            llm_client=FailingClient(),
            num_queries=3,
        )

        result = await generator.transform("test query")

        # Should fall back to original
        assert "test query" in result.transformed

    @pytest.mark.asyncio
    async def test_strategy_property(self):
        """Test strategy property."""
        mock_client = MockLLMClient()
        generator = MultiQueryGenerator(llm_client=mock_client)
        assert generator.strategy == TransformationStrategy.MULTI_QUERY


class TestHyDEGenerator:
    """Test HyDEGenerator."""

    @pytest.mark.asyncio
    async def test_generate_hypothetical_document(self):
        """Test generating hypothetical document."""
        mock_client = MockLLMClient(
            responses=[
                "Caching is a technique that stores frequently accessed data "
                "in memory for faster retrieval. It reduces latency and improves "
                "application performance.",
            ],
        )

        hyde = HyDEGenerator(llm_client=mock_client)

        result = await hyde.transform("How does caching work?")

        assert result.original == "How does caching work?"
        assert len(result.transformed) == 1
        assert "Caching" in result.transformed[0]

    @pytest.mark.asyncio
    async def test_multiple_documents(self):
        """Test generating multiple hypothetical documents."""
        mock_client = MockLLMClient(
            responses=[
                "Document 1 about caching",
                "Document 2 about caching",
                "Document 3 about caching",
            ],
        )

        hyde = HyDEGenerator(
            llm_client=mock_client,
            num_documents=3,
        )

        result = await hyde.transform("caching")

        assert len(result.transformed) == 3

    @pytest.mark.asyncio
    async def test_doc_length_short(self):
        """Test short document length."""
        mock_client = MockLLMClient(responses=["Short response"])

        hyde = HyDEGenerator(
            llm_client=mock_client,
            doc_length="short",
        )

        result = await hyde.transform("test")

        assert result.metadata["doc_length"] == "short"

    @pytest.mark.asyncio
    async def test_doc_length_long(self):
        """Test long document length."""
        mock_client = MockLLMClient(responses=["Long response"])

        hyde = HyDEGenerator(
            llm_client=mock_client,
            doc_length="long",
        )

        result = await hyde.transform("test")

        assert result.metadata["doc_length"] == "long"

    @pytest.mark.asyncio
    async def test_generation_failure_fallback(self):
        """Test fallback when generation fails."""

        class FailingClient:
            async def complete(self, messages, temperature=0.7, max_tokens=None):
                raise ConnectionError("Failed")

        hyde = HyDEGenerator(llm_client=FailingClient())

        result = await hyde.transform("test query")

        # Should fall back to original query
        assert "test query" in result.transformed

    @pytest.mark.asyncio
    async def test_strategy_property(self):
        """Test strategy property."""
        mock_client = MockLLMClient()
        hyde = HyDEGenerator(llm_client=mock_client)
        assert hyde.strategy == TransformationStrategy.HYDE


class TestQueryRewriter:
    """Test QueryRewriter."""

    @pytest.mark.asyncio
    async def test_rewrite_query(self):
        """Test rewriting a query."""
        mock_client = MockLLMClient(
            responses=["How to debug and fix software bugs"],
        )

        rewriter = QueryRewriter(llm_client=mock_client)

        result = await rewriter.transform("how 2 fix bug")

        assert result.original == "how 2 fix bug"
        assert len(result.transformed) == 1
        assert "debug" in result.transformed[0].lower()

    @pytest.mark.asyncio
    async def test_custom_instructions(self):
        """Test custom rewriting instructions."""
        mock_client = MockLLMClient(responses=["Technical query version"])

        custom_instructions = "Rewrite in technical language"
        rewriter = QueryRewriter(
            llm_client=mock_client,
            instructions=custom_instructions,
        )

        result = await rewriter.transform("simple query")

        assert result.metadata["instructions_used"] is True

    @pytest.mark.asyncio
    async def test_low_temperature(self):
        """Test low temperature for consistent rewrites."""
        mock_client = MockLLMClient(responses=["Rewritten query"])

        rewriter = QueryRewriter(
            llm_client=mock_client,
            temperature=0.1,
        )

        result = await rewriter.transform("test")

        assert result.transformed[0] == "Rewritten query"

    @pytest.mark.asyncio
    async def test_rewrite_failure_fallback(self):
        """Test fallback on rewrite failure."""

        class FailingClient:
            async def complete(self, messages, temperature=0.7, max_tokens=None):
                raise ConnectionError("Failed")

        rewriter = QueryRewriter(llm_client=FailingClient())

        result = await rewriter.transform("original query")

        # Should fall back to original
        assert result.transformed[0] == "original query"

    @pytest.mark.asyncio
    async def test_invalid_rewrite_fallback(self):
        """Test fallback when rewrite is too short."""
        mock_client = MockLLMClient(responses=["ab"])  # Too short

        rewriter = QueryRewriter(llm_client=mock_client)

        result = await rewriter.transform("test query")

        assert result.transformed[0] == "test query"

    @pytest.mark.asyncio
    async def test_strategy_property(self):
        """Test strategy property."""
        mock_client = MockLLMClient()
        rewriter = QueryRewriter(llm_client=mock_client)
        assert rewriter.strategy == TransformationStrategy.REWRITE


class TestCustomQueryTransformer:
    """Test CustomQueryTransformer."""

    @pytest.mark.asyncio
    async def test_custom_function(self):
        """Test custom transformation function."""

        def add_prefix(query: str) -> list:
            return [f"Search: {query}", f"Find: {query}"]

        transformer = CustomQueryTransformer(
            transform_fn=add_prefix,
            strategy_name="prefix_adder",
        )

        result = await transformer.transform("test")

        assert len(result.transformed) == 2
        assert result.transformed[0] == "Search: test"
        assert result.transformed[1] == "Find: test"

    @pytest.mark.asyncio
    async def test_single_result_conversion(self):
        """Test converting single result to list."""

        def single_transform(query: str) -> str:
            return f"Modified: {query}"

        transformer = CustomQueryTransformer(transform_fn=single_transform)

        result = await transformer.transform("test")

        assert isinstance(result.transformed, list)
        assert result.transformed[0] == "Modified: test"

    @pytest.mark.asyncio
    async def test_error_fallback(self):
        """Test fallback on transformation error."""

        def failing_transform(query: str) -> list:
            raise OSError("Transform failed")

        transformer = CustomQueryTransformer(transform_fn=failing_transform)

        result = await transformer.transform("test")

        # Should fall back to original
        assert result.transformed[0] == "test"

    @pytest.mark.asyncio
    async def test_strategy_metadata(self):
        """Test strategy metadata."""
        transformer = CustomQueryTransformer(
            transform_fn=lambda q: [q],
            strategy_name="my_custom_strategy",
        )

        result = await transformer.transform("test")

        assert result.metadata["strategy_name"] == "my_custom_strategy"

    @pytest.mark.asyncio
    async def test_strategy_property(self):
        """Test strategy property."""
        transformer = CustomQueryTransformer(transform_fn=lambda q: [q])
        assert transformer.strategy == TransformationStrategy.CUSTOM


class TestTransformationPipeline:
    """Test TransformationPipeline."""

    @pytest.mark.asyncio
    async def test_multiple_transformers(self):
        """Test pipeline with multiple transformers."""
        expander = QueryExpander(
            expansion_terms={"ML": ["machine learning"]},
        )

        mock_client = MockLLMClient(responses=["Query variation"])
        multi_gen = MultiQueryGenerator(llm_client=mock_client, num_queries=1)

        pipeline = TransformationPipeline(
            transformers=[expander, multi_gen],
        )

        results = await pipeline.transform("ML test")

        assert len(results) == 2
        assert results[0].strategy == TransformationStrategy.EXPANSION
        assert results[1].strategy == TransformationStrategy.MULTI_QUERY

    @pytest.mark.asyncio
    async def test_transform_combined(self):
        """Test combining results from multiple transformers."""
        expander = QueryExpander(
            expansion_terms={"test": ["example"]},
        )

        def custom_fn(q: str) -> list:
            return [f"custom: {q}"]

        custom = CustomQueryTransformer(transform_fn=custom_fn)

        pipeline = TransformationPipeline(
            transformers=[expander, custom],
            combine_results=True,
        )

        combined = await pipeline.transform_combined("test")

        # Should have deduplicated results from both transformers
        assert len(combined) >= 2
        assert "test" in combined or "example" in combined

    @pytest.mark.asyncio
    async def test_max_total_queries(self):
        """Test max_total_queries limit."""

        def many_queries(q: str) -> list:
            return list(map(lambda i: f"q{i}", range(20)))

        transformer = CustomQueryTransformer(transform_fn=many_queries)

        pipeline = TransformationPipeline(
            transformers=[transformer],
            max_total_queries=5,
        )

        combined = await pipeline.transform_combined("test")

        assert len(combined) <= 5

    @pytest.mark.asyncio
    async def test_deduplication(self):
        """Test that combined results are deduplicated."""

        def duplicate_fn(q: str) -> list:
            return [q, q, "other", q]

        transformer = CustomQueryTransformer(transform_fn=duplicate_fn)

        pipeline = TransformationPipeline(transformers=[transformer])

        combined = await pipeline.transform_combined("test")

        # Should deduplicate
        assert combined.count("test") == 1

    @pytest.mark.asyncio
    async def test_empty_transformers(self):
        """Test pipeline with no transformers."""
        pipeline = TransformationPipeline(transformers=[])

        results = await pipeline.transform("test")

        assert len(results) == 0


class TestCreateTransformer:
    """Test create_transformer factory function."""

    def test_create_expander(self):
        """Test creating QueryExpander."""
        transformer = create_transformer(
            TransformationStrategy.EXPANSION,
            max_expansions=3,
        )

        assert isinstance(transformer, QueryExpander)
        assert transformer.max_expansions == 3

    def test_create_multi_query(self):
        """Test creating MultiQueryGenerator."""
        mock_client = MockLLMClient()
        transformer = create_transformer(
            TransformationStrategy.MULTI_QUERY,
            llm_client=mock_client,
            num_queries=5,
        )

        assert isinstance(transformer, MultiQueryGenerator)
        assert transformer.num_queries == 5

    def test_create_hyde(self):
        """Test creating HyDEGenerator."""
        mock_client = MockLLMClient()
        transformer = create_transformer(
            TransformationStrategy.HYDE,
            llm_client=mock_client,
            doc_length="long",
        )

        assert isinstance(transformer, HyDEGenerator)
        assert transformer.doc_length == "long"

    def test_create_rewriter(self):
        """Test creating QueryRewriter."""
        mock_client = MockLLMClient()
        transformer = create_transformer(
            TransformationStrategy.REWRITE,
            llm_client=mock_client,
            temperature=0.1,
        )

        assert isinstance(transformer, QueryRewriter)
        assert transformer.temperature == 0.1

    def test_multi_query_requires_llm(self):
        """Test that MultiQueryGenerator requires llm_client."""
        with pytest.raises(ValueError, match="requires llm_client"):
            create_transformer(TransformationStrategy.MULTI_QUERY)

    def test_hyde_requires_llm(self):
        """Test that HyDEGenerator requires llm_client."""
        with pytest.raises(ValueError, match="requires llm_client"):
            create_transformer(TransformationStrategy.HYDE)

    def test_rewriter_requires_llm(self):
        """Test that QueryRewriter requires llm_client."""
        with pytest.raises(ValueError, match="requires llm_client"):
            create_transformer(TransformationStrategy.REWRITE)

    def test_unknown_strategy(self):
        """Test unknown strategy raises error."""
        with pytest.raises(ValueError, match="Unknown strategy"):
            create_transformer("invalid_strategy")


class TestIntegration:
    """Integration tests for query transformation."""

    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """Test full transformation pipeline."""
        # Setup transformers
        expander = QueryExpander(
            expansion_terms={
                "ML": ["machine learning", "AI"],
            },
        )

        mock_client = MockLLMClient(
            responses=[
                "What is machine learning?\nExplain ML concepts",
                "Machine learning is a subset of AI...",
            ],
        )

        multi_gen = MultiQueryGenerator(llm_client=mock_client, num_queries=2)
        hyde = HyDEGenerator(llm_client=mock_client)

        # Create pipeline
        pipeline = TransformationPipeline(
            transformers=[expander, multi_gen, hyde],
            max_total_queries=10,
        )

        # Transform query
        results = await pipeline.transform("ML basics")

        assert len(results) == 3
        assert all(isinstance(r, TransformedQuery) for r in results)

    @pytest.mark.asyncio
    async def test_combined_transformation(self):
        """Test combined transformation results."""
        expander = QueryExpander(
            expansion_terms={"test": ["example", "demo"]},
        )

        pipeline = TransformationPipeline(
            transformers=[expander],
            max_total_queries=5,
        )

        combined = await pipeline.transform_combined("test query")

        # Should have original + expansions
        assert len(combined) >= 2
        assert any("test" in q or "example" in q or "demo" in q for q in combined)
