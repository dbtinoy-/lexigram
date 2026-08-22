from __future__ import annotations

from _test_query_transformation_support import (
    MockLLMClient,
)
import pytest

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
