"""Unit tests for query transformers."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.rag.query.base import TransformationStrategy
from lexigram.ai.rag.query.transformers import (
    HyDEGenerator,
    MultiQueryGenerator,
    QueryExpander,
    QueryRewriter,
)


class TestQueryExpander:
    """Tests for QueryExpander class."""

    def test_expand_with_predefined_terms(self) -> None:
        """Test expand with predefined expansion terms."""
        expander = QueryExpander(
            expansion_terms={
                "python": ["Python programming", "Python language"],
                "async": ["asynchronous", "concurrent"],
            },
        )

        result = expander.strategy
        assert result == TransformationStrategy.EXPANSION

    def test_expand_includes_original_query(self) -> None:
        """Test that original query is included by default."""
        expander = QueryExpander(
            expansion_terms={"test": ["testing"]},
            include_original=True,
        )

        assert expander.include_original is True

    def test_expand_max_expansions(self) -> None:
        """Test max expansions limit."""
        expander = QueryExpander(
            expansion_terms={"test": ["a", "b", "c", "d", "e"]},
            max_expansions=3,
        )

        assert expander.max_expansions == 3

    def test_expand_without_llm_client(self) -> None:
        """Test expand works without LLM client (fallback only)."""
        expander = QueryExpander(
            expansion_terms={},
            llm_client=None,
        )

        assert expander.llm_client is None

    @pytest.mark.asyncio
    async def test_expand_fallback_on_llm_error(self) -> None:
        """Test fallback behavior when LLM expansion fails."""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(
            side_effect=Exception("LLM error"),
        )

        expander = QueryExpander(
            expansion_terms={},
            llm_client=mock_llm,
            max_expansions=3,
        )

        result = await expander.transform("test query")

        assert result.original == "test query"
        assert result.strategy == TransformationStrategy.EXPANSION
        assert "test query" in result.transformed

    @pytest.mark.asyncio
    async def test_expand_llm_based_expansion(self) -> None:
        """Test LLM-based query expansion."""
        mock_llm = MagicMock()
        mock_result = MagicMock()
        mock_result.is_err = MagicMock(return_value=False)
        mock_result.unwrap = MagicMock(
            return_value="alternative1\nalternative2\nalternative3"
        )
        mock_llm.complete = AsyncMock(return_value=mock_result)

        expander = QueryExpander(
            expansion_terms={},
            llm_client=mock_llm,
            max_expansions=3,
        )

        result = await expander.transform("test query")

        assert result.original == "test query"
        assert "test query" in result.transformed


class TestMultiQueryGenerator:
    """Tests for MultiQueryGenerator class."""

    @pytest.mark.asyncio
    async def test_generate_queries_basic(self) -> None:
        """Test basic multi-query generation."""
        mock_llm = MagicMock()
        mock_result = MagicMock()
        mock_result.is_err = MagicMock(return_value=False)
        mock_result.unwrap = MagicMock(
            return_value="query variant 1\nquery variant 2\nquery variant 3"
        )
        mock_llm.complete = AsyncMock(return_value=mock_result)

        generator = MultiQueryGenerator(
            llm_client=mock_llm,
            num_queries=3,
            include_original=True,
        )

        result = await generator.transform("original query")

        assert result.original == "original query"
        assert result.strategy == TransformationStrategy.MULTI_QUERY

    @pytest.mark.asyncio
    async def test_generate_queries_no_duplicates(self) -> None:
        """Test that duplicate queries are filtered."""
        mock_llm = MagicMock()
        mock_result = MagicMock()
        mock_result.is_err = MagicMock(return_value=False)
        mock_result.unwrap = MagicMock(
            return_value="original query\nvariant1\nvariant1"
        )
        mock_llm.complete = AsyncMock(return_value=mock_result)

        generator = MultiQueryGenerator(
            llm_client=mock_llm,
            num_queries=2,
            include_original=True,
        )

        result = await generator.transform("original query")

        unique_queries = set(result.transformed)
        assert len(result.transformed) == len(unique_queries)

    @pytest.mark.asyncio
    async def test_generate_queries_fallback_on_error(self) -> None:
        """Test fallback to original query on error."""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(side_effect=RuntimeError("LLM error"))

        generator = MultiQueryGenerator(
            llm_client=mock_llm,
            num_queries=3,
            include_original=True,
        )

        result = await generator.transform("original query")

        assert result.original == "original query"
        assert "original query" in result.transformed


class TestQueryRewriter:
    """Tests for QueryRewriter class."""

    @pytest.mark.asyncio
    async def test_rewrite_basic(self) -> None:
        """Test basic query rewriting."""
        mock_llm = MagicMock()
        mock_result = MagicMock()
        mock_result.is_err = MagicMock(return_value=False)
        mock_result.unwrap = MagicMock(return_value="rewritten query")
        mock_llm.complete = AsyncMock(return_value=mock_result)

        rewriter = QueryRewriter(
            llm_client=mock_llm,
            instructions="Improve the query",
        )

        result = await rewriter.transform("original query")

        assert result.original == "original query"
        assert len(result.transformed) >= 1
        assert result.strategy == TransformationStrategy.REWRITE

    @pytest.mark.asyncio
    async def test_rewrite_fallback_on_error(self) -> None:
        """Test fallback to original on error."""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(side_effect=OSError("Error"))

        rewriter = QueryRewriter(
            llm_client=mock_llm,
        )

        result = await rewriter.transform("original query")

        assert "original query" in result.transformed

    @pytest.mark.asyncio
    async def test_rewrite_preserves_short_responses(self) -> None:
        """Test that very short responses fall back to original."""
        mock_llm = MagicMock()
        mock_result = MagicMock()
        mock_result.is_err = MagicMock(return_value=False)
        mock_result.unwrap = MagicMock(return_value="ab")
        mock_llm.complete = AsyncMock(return_value=mock_result)

        rewriter = QueryRewriter(llm_client=mock_llm)

        result = await rewriter.transform("test query")

        assert result.transformed[0] == "test query"


class TestHyDEGenerator:
    """Tests for HyDEGenerator class."""

    @pytest.mark.asyncio
    async def test_generate_hypothetical_docs(self) -> None:
        """Test generation of hypothetical documents."""
        mock_llm = MagicMock()
        mock_result = MagicMock()
        mock_result.is_err = MagicMock(return_value=False)
        mock_result.unwrap = MagicMock(
            return_value="This is a detailed answer explaining the concept..."
        )
        mock_llm.complete = AsyncMock(return_value=mock_result)

        generator = HyDEGenerator(
            llm_client=mock_llm,
            num_documents=1,
            doc_length="medium",
        )

        result = await generator.transform("What is Python?")

        assert result.original == "What is Python?"
        assert result.strategy == TransformationStrategy.HYDE
        assert len(result.transformed) >= 1

    @pytest.mark.asyncio
    async def test_generate_multiple_documents(self) -> None:
        """Test generation of multiple documents."""
        mock_llm = MagicMock()
        mock_result = MagicMock()
        mock_result.is_err = MagicMock(return_value=False)
        mock_result.unwrap = MagicMock(return_value="Document content")
        mock_llm.complete = AsyncMock(return_value=mock_result)

        generator = HyDEGenerator(
            llm_client=mock_llm,
            num_documents=3,
        )

        result = await generator.transform("test query")

        assert len(result.transformed) >= 1

    @pytest.mark.asyncio
    async def test_generate_fallback_on_error(self) -> None:
        """Test fallback behavior on generation error."""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(side_effect=RuntimeError("Generation failed"))

        generator = HyDEGenerator(llm_client=mock_llm)

        result = await generator.transform("test query")

        assert result.original == "test query"
        assert "test query" in result.transformed


class TestQueryTransformersExports:
    """Tests for query transformers module exports."""

    def test_all_exports(self) -> None:
        """Test that all expected exports are available."""
        from lexigram.ai.rag import query

        expected = [
            "QueryExpander",
            "MultiQueryGenerator",
            "QueryRewriter",
            "HyDEGenerator",
        ]
        for name in expected:
            assert hasattr(query.transformers, name)
