"""Tests for EmbeddingDistanceEvaluator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.evaluation.evaluators.embedding_distance import EmbeddingDistanceEvaluator
from lexigram.contracts.ai.evaluation import EvaluationScoreType


class TestEmbeddingDistanceEvaluator:
    """Tests for embedding-based similarity evaluation."""

    def test_name_returns_embedding_distance(self) -> None:
        evaluator = EmbeddingDistanceEvaluator()
        assert evaluator.name == "embedding_distance"

    def test_score_type_is_semantic_similarity(self) -> None:
        evaluator = EmbeddingDistanceEvaluator()
        assert evaluator._score_type == EvaluationScoreType.SEMANTIC_SIMILARITY

    @pytest.mark.asyncio
    async def test_evaluate_without_client_returns_zero_score(self) -> None:
        evaluator = EmbeddingDistanceEvaluator()
        result = await evaluator.evaluate("q", "answer", "reference")
        assert result.is_ok()
        er = result.unwrap()
        assert er.score == 0.0
        assert er.metrics.get("error") == "embedding_client_not_available"

    @pytest.mark.asyncio
    async def test_evaluate_identical_texts_returns_high_similarity(self) -> None:
        mock_client = MagicMock()
        vec = [1.0, 0.0, 0.0]
        mock_client.embed = AsyncMock(return_value=[vec])
        evaluator = EmbeddingDistanceEvaluator(embedding_client=mock_client)
        result = await evaluator.evaluate("q", "same", "same")
        assert result.is_ok()
        assert result.unwrap().score == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_evaluate_orthogonal_vectors_returns_zero(self) -> None:
        mock_client = MagicMock()
        call_count = 0

        async def embed_side_effect(texts):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [[[1.0, 0.0]]]
            return [[[0.0, 1.0]]]

        mock_client.embed = AsyncMock(side_effect=embed_side_effect)
        evaluator = EmbeddingDistanceEvaluator(embedding_client=mock_client)
        result = await evaluator.evaluate("q", "output", "reference")
        assert result.is_ok()
        assert result.unwrap().score == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_evaluate_handles_embedding_exception(self) -> None:
        mock_client = MagicMock()
        mock_client.embed = AsyncMock(side_effect=RuntimeError("API error"))
        evaluator = EmbeddingDistanceEvaluator(embedding_client=mock_client)
        result = await evaluator.evaluate("q", "output", "reference")
        assert result.is_ok()
        er = result.unwrap()
        assert er.score == 0.0
        assert "error" in er.metrics

    def test_set_embedding_client_updates_client(self) -> None:
        evaluator = EmbeddingDistanceEvaluator()
        assert evaluator._embedding_client is None
        mock_client = MagicMock()
        evaluator.set_embedding_client(mock_client)
        assert evaluator._embedding_client is mock_client

    def test_cosine_similarity_identical_vectors(self) -> None:
        evaluator = EmbeddingDistanceEvaluator()
        assert evaluator._cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)

    def test_cosine_similarity_zero_vector_returns_zero(self) -> None:
        evaluator = EmbeddingDistanceEvaluator()
        assert evaluator._cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0

    @pytest.mark.asyncio
    async def test_evaluate_empty_embeddings_returns_zero(self) -> None:
        mock_client = MagicMock()
        mock_client.embed = AsyncMock(return_value=[])
        evaluator = EmbeddingDistanceEvaluator(embedding_client=mock_client)
        result = await evaluator.evaluate("q", "out", "ref")
        assert result.is_ok()
        assert result.unwrap().score == 0.0
