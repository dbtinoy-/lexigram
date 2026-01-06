"""Unit tests for RAGPipeline."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.result import Err, Ok
from lexigram_example_ai.pipelines.rag_pipeline import (
    RAGPipeline,
    RagQuery,
    RagAnswer,
)


def _make_hit(text: str = "doc text", score: float = 0.9) -> MagicMock:
    """Create a minimal stub search hit."""
    hit = MagicMock()
    hit.score = score
    hit.document = MagicMock()
    hit.document.text = text
    hit.document.metadata = {"source": "test"}
    return hit


class TestRAGPipelineRun:
    """Tests for RAGPipeline.run()."""

    @pytest.mark.asyncio
    async def test_returns_ok_on_success(self, rag_pipeline):
        """Full pipeline returns Ok(RagAnswer) when all stages succeed."""
        result = await rag_pipeline.run(RagQuery(query="What is Lexigram?"))

        assert result.is_ok()
        answer = result.unwrap()
        assert isinstance(answer, RagAnswer)
        assert answer.query == "What is Lexigram?"
        assert answer.model == "stub"

    @pytest.mark.asyncio
    async def test_sources_populated_from_hits(
        self, mock_llm, mock_embedder, mock_vector_store, stub_completion
    ):
        """Sources in the answer reflect retrieved documents."""
        hits = [_make_hit("first doc", 0.9), _make_hit("second doc", 0.7)]
        mock_vector_store.search = AsyncMock(return_value=Ok(hits))

        pipeline = RAGPipeline(
            llm=mock_llm,
            embedder=mock_embedder,
            vector_store=mock_vector_store,
        )
        result = await pipeline.run(RagQuery(query="test"))

        assert result.is_ok()
        sources = result.unwrap().sources
        assert len(sources) == 2
        assert sources[0].text == "first doc"
        assert sources[0].score == pytest.approx(0.9)
        assert sources[1].text == "second doc"

    @pytest.mark.asyncio
    async def test_returns_err_on_embed_failure(
        self, mock_llm, mock_vector_store
    ):
        """Pipeline returns Err when the embedding step fails."""
        failing_embedder = MagicMock()
        failing_embedder.embed = AsyncMock(side_effect=RuntimeError("embed failed"))

        pipeline = RAGPipeline(
            llm=mock_llm,
            embedder=failing_embedder,
            vector_store=mock_vector_store,
        )
        result = await pipeline.run(RagQuery(query="fail me"))

        assert result.is_err()

    @pytest.mark.asyncio
    async def test_returns_err_on_retrieval_failure(
        self, mock_llm, mock_embedder
    ):
        """Pipeline returns Err when the vector store search fails."""
        from lexigram.contracts.ai.rag import RetrievalError

        failing_store = MagicMock()
        failing_store.search = AsyncMock(return_value=Err(RetrievalError("db error")))

        pipeline = RAGPipeline(
            llm=mock_llm,
            embedder=mock_embedder,
            vector_store=failing_store,
        )
        result = await pipeline.run(RagQuery(query="fail me"))

        assert result.is_err()

    @pytest.mark.asyncio
    async def test_returns_err_on_synthesis_failure(
        self, mock_embedder, mock_vector_store
    ):
        """Pipeline returns Err when the LLM synthesis step fails."""
        from lexigram.contracts.ai.exceptions import LLMError

        failing_llm = MagicMock()
        failing_llm.complete = AsyncMock(
            return_value=Err(LLMError("synthesis failed"))
        )

        pipeline = RAGPipeline(
            llm=failing_llm,
            embedder=mock_embedder,
            vector_store=mock_vector_store,
        )
        result = await pipeline.run(RagQuery(query="synthesise me"))

        assert result.is_err()

    @pytest.mark.asyncio
    async def test_empty_vector_store_still_synthesises(self, rag_pipeline):
        """Pipeline still calls the LLM even with zero retrieved documents."""
        # mock_vector_store already returns Ok([]) — no docs
        result = await rag_pipeline.run(RagQuery(query="anything"))

        assert result.is_ok()
        # LLM was called
        rag_pipeline._llm.complete.assert_awaited_once()


__all__: list[str] = []
