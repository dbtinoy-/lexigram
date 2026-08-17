"""Unit tests for pruning types."""

from __future__ import annotations

import pytest

from lexigram.ai.memory.pruning.types import PruningStrategy, PruningResult

from helpers import make_entry


class TestPruningStrategy:
    def test_all_strategy_values(self) -> None:
        assert PruningStrategy.RECENCY == "recency"
        assert PruningStrategy.RELEVANCE == "relevance"
        assert PruningStrategy.HYBRID == "hybrid"

    def test_strategy_from_string(self) -> None:
        assert PruningStrategy("recency") == PruningStrategy.RECENCY
        assert PruningStrategy("relevance") == PruningStrategy.RELEVANCE
        assert PruningStrategy("hybrid") == PruningStrategy.HYBRID


class TestPruningResult:
    def test_result_fields(self) -> None:
        entries = [make_entry("test")]
        result = PruningResult(
            kept=entries,
            pruned_count=5,
            original_count=10,
            token_budget=1000,
            strategy=PruningStrategy.RECENCY,
            metadata={"test": True},
        )

        assert result.kept == entries
        assert result.pruned_count == 5
        assert result.original_count == 10
        assert result.token_budget == 1000
        assert result.strategy == PruningStrategy.RECENCY
        assert result.metadata == {"test": True}

    def test_result_is_frozen(self) -> None:
        result = PruningResult(
            kept=[],
            pruned_count=0,
            original_count=0,
            token_budget=0,
            strategy=PruningStrategy.RECENCY,
        )

        with pytest.raises(AttributeError):
            result.pruned_count = 1  # type: ignore[assignment]