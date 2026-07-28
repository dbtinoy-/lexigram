"""Unit tests for concrete retrieval strategies."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram.ai.rag.retrieval.strategies.mmr import MMRRetrievalStrategy
from lexigram.ai.rag.retrieval.strategies.vector import VectorRetrievalStrategy
from lexigram.ai.rag.retrieval.strategy_registry import RetrievalStrategyRegistry


def make_result(score: float, doc_id: str = "doc") -> MagicMock:
    """Build a minimal SearchResultProtocol-compatible mock."""
    r = MagicMock()
    r.score = score
    r.id = doc_id
    return r


class TestVectorRetrievalStrategy:
    @pytest.mark.asyncio
    async def test_returns_top_k_by_score(self) -> None:
        strategy = VectorRetrievalStrategy()
        candidates = [
            make_result(0.5, "a"),
            make_result(0.9, "b"),
            make_result(0.3, "c"),
        ]
        result = await strategy.retrieve("query", candidates, top_k=2)
        assert len(result) == 2
        assert result[0].id == "b"  # highest score first
        assert result[1].id == "a"

    @pytest.mark.asyncio
    async def test_empty_candidates(self) -> None:
        result = await VectorRetrievalStrategy().retrieve("q", [], top_k=5)
        assert result == []

    @pytest.mark.asyncio
    async def test_fewer_than_top_k(self) -> None:
        candidates = [make_result(0.8, "a"), make_result(0.6, "b")]
        result = await VectorRetrievalStrategy().retrieve("q", candidates, top_k=10)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_top_k_zero_returns_empty(self) -> None:
        candidates = [make_result(0.8, "a")]
        result = await VectorRetrievalStrategy().retrieve("q", candidates, top_k=0)
        assert result == []

    @pytest.mark.asyncio
    async def test_original_list_not_mutated(self) -> None:
        candidates = [make_result(0.5, "a"), make_result(0.9, "b")]
        original_order = list(candidates)
        await VectorRetrievalStrategy().retrieve("q", candidates, top_k=2)
        assert candidates == original_order


class TestMMRRetrievalStrategy:
    @pytest.mark.asyncio
    async def test_returns_top_k(self) -> None:
        strategy = MMRRetrievalStrategy(lambda_param=0.5)
        candidates = [
            make_result(s, f"doc{i}") for i, s in enumerate([0.9, 0.8, 0.7, 0.6, 0.5])
        ]
        result = await strategy.retrieve("query", candidates, top_k=3)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_lambda_one_seeds_with_highest_score(self) -> None:
        """lambda=1.0 maximises relevance — first result is the highest-scored candidate."""
        strategy = MMRRetrievalStrategy(lambda_param=1.0)
        candidates = [
            make_result(0.9, "a"),
            make_result(0.5, "b"),
            make_result(0.3, "c"),
        ]
        result = await strategy.retrieve("query", candidates, top_k=2)
        assert result[0].id == "a"

    @pytest.mark.asyncio
    async def test_empty_candidates(self) -> None:
        result = await MMRRetrievalStrategy().retrieve("q", [], top_k=5)
        assert result == []

    @pytest.mark.asyncio
    async def test_fewer_than_top_k(self) -> None:
        candidates = [make_result(0.9, "a"), make_result(0.5, "b")]
        result = await MMRRetrievalStrategy().retrieve("q", candidates, top_k=10)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_single_candidate(self) -> None:
        candidates = [make_result(0.8, "only")]
        result = await MMRRetrievalStrategy().retrieve("q", candidates, top_k=5)
        assert len(result) == 1
        assert result[0].id == "only"

    @pytest.mark.asyncio
    async def test_default_lambda_param(self) -> None:
        strategy = MMRRetrievalStrategy()
        assert strategy._lambda == 0.5


class TestRetrievalStrategyRegistryWithDefaults:
    def test_with_defaults_registers_vector(self) -> None:
        registry = RetrievalStrategyRegistry.with_defaults()
        strategy = registry.instantiate("vector")
        assert isinstance(strategy, VectorRetrievalStrategy)

    def test_with_defaults_registers_mmr(self) -> None:
        registry = RetrievalStrategyRegistry.with_defaults()
        strategy = registry.instantiate("mmr")
        assert isinstance(strategy, MMRRetrievalStrategy)

    def test_mmr_instantiated_with_custom_lambda(self) -> None:
        registry = RetrievalStrategyRegistry.with_defaults()
        strategy = registry.instantiate("mmr", lambda_param=0.8)
        assert isinstance(strategy, MMRRetrievalStrategy)
        assert strategy._lambda == 0.8

    def test_empty_registry_has_no_defaults(self) -> None:
        registry = RetrievalStrategyRegistry()
        assert set(registry.all_keys()) == set()
