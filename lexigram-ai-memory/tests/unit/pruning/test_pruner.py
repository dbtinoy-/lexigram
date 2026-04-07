"""Tests for DynamicContextPruner."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.memory.pruning.pruner import DynamicContextPruner
from lexigram.ai.memory.pruning.scorer import HybridScorerImpl, RecencyScorerImpl
from lexigram.ai.memory.pruning.types import PruningStrategy
from lexigram.contracts.ai.llm import TokenCounterProtocol
from lexigram.contracts.ai.memory import MemoryEntry


@pytest.fixture
def mock_token_counter() -> MagicMock:
    """Mock TokenCounterProtocol."""
    counter = MagicMock(spec=TokenCounterProtocol)
    counter.count = MagicMock(return_value=10)
    return counter


@pytest.fixture
def sample_entries() -> list[MemoryEntry]:
    """Create sample memory entries for testing."""
    now = datetime.now(timezone.utc)
    return [
        MemoryEntry(
            id="entry-1",
            content="First entry with some content",
            role="user",
            timestamp=now,
            importance=0.5,
        ),
        MemoryEntry(
            id="entry-2",
            content="Second entry with longer content " * 10,
            role="assistant",
            timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
            importance=0.7,
        ),
        MemoryEntry(
            id="entry-3",
            content="Third entry",
            role="system",
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            importance=0.3,
        ),
    ]


class TestDynamicContextPruner:
    """Tests for DynamicContextPruner."""

    @pytest.mark.asyncio
    async def test_prune_empty_list_returns_empty_result(
        self, mock_token_counter: MagicMock
    ) -> None:
        """Test pruning an empty list returns an empty result."""
        pruner = DynamicContextPruner(token_counter=mock_token_counter)

        result = await pruner.prune(
            entries=[],
            token_budget=100,
        )

        assert result.kept == []
        assert result.pruned_count == 0
        assert result.original_count == 0
        assert result.token_budget == 100

    @pytest.mark.asyncio
    async def test_prune_all_fit_within_budget(
        self,
        mock_token_counter: MagicMock,
        sample_entries: list[MemoryEntry],
    ) -> None:
        """Test all entries fit within budget."""
        mock_token_counter.count = MagicMock(return_value=10)
        pruner = DynamicContextPruner(token_counter=mock_token_counter)

        # Budget of 100 tokens, 3 entries * 10 tokens = 30 tokens total
        result = await pruner.prune(
            entries=sample_entries,
            token_budget=100,
        )

        assert len(result.kept) == 3
        assert result.pruned_count == 0
        assert result.original_count == 3

    @pytest.mark.asyncio
    async def test_prune_trims_to_budget(
        self,
        mock_token_counter: MagicMock,
        sample_entries: list[MemoryEntry],
    ) -> None:
        """Test entries are trimmed to fit the budget."""
        # Each entry is 10 tokens, budget is 25 tokens = room for 2 entries
        mock_token_counter.count = MagicMock(return_value=10)
        pruner = DynamicContextPruner(
            token_counter=mock_token_counter,
            default_strategy=PruningStrategy.RECENCY,
        )

        result = await pruner.prune(
            entries=sample_entries,
            token_budget=25,
        )

        # Should keep 2 entries and prune 1
        assert len(result.kept) == 2
        assert result.pruned_count == 1
        assert result.original_count == 3

    @pytest.mark.asyncio
    async def test_prune_uses_default_strategy(
        self,
        mock_token_counter: MagicMock,
        sample_entries: list[MemoryEntry],
    ) -> None:
        """Test default strategy is used when none specified."""
        mock_token_counter.count = MagicMock(return_value=10)
        pruner = DynamicContextPruner(
            token_counter=mock_token_counter,
            default_strategy=PruningStrategy.HYBRID,
        )

        result = await pruner.prune(
            entries=sample_entries,
            token_budget=100,
        )

        assert result.strategy == PruningStrategy.HYBRID

    @pytest.mark.asyncio
    async def test_prune_overrides_strategy(
        self,
        mock_token_counter: MagicMock,
        sample_entries: list[MemoryEntry],
    ) -> None:
        """Test strategy kwarg overrides default."""
        mock_token_counter.count = MagicMock(return_value=10)
        pruner = DynamicContextPruner(
            token_counter=mock_token_counter,
            default_strategy=PruningStrategy.HYBRID,
        )

        result = await pruner.prune(
            entries=sample_entries,
            token_budget=100,
            strategy=PruningStrategy.RECENCY,
        )

        assert result.strategy == PruningStrategy.RECENCY

    def test_recency_scorer_returns_float(
        self, sample_entries: list[MemoryEntry]
    ) -> None:
        """Test RecencyScorerImpl returns a float."""
        scorer = RecencyScorerImpl()

        for entry in sample_entries:
            score = scorer.score(entry)
            assert isinstance(score, (int, float))

    def test_hybrid_scorer_blends_scores(
        self, sample_entries: list[MemoryEntry]
    ) -> None:
        """Test HybridScorerImpl blends recency and content length."""
        scorer = HybridScorerImpl(recency_weight=0.6, relevance_weight=0.4)

        # Test batch scoring
        batch_scores = scorer.score_batch(sample_entries)
        assert len(batch_scores) == len(sample_entries)
        for score in batch_scores:
            assert isinstance(score, (int, float))
            assert 0 <= score <= 1.0

        # Test single entry scoring
        for entry in sample_entries:
            score = scorer.score(entry)
            assert isinstance(score, (int, float))

    @pytest.mark.asyncio
    async def test_prune_zero_budget_returns_empty(
        self,
        mock_token_counter: MagicMock,
        sample_entries: list[MemoryEntry],
    ) -> None:
        """Test token_budget=0 returns an empty kept list."""
        mock_token_counter.count = MagicMock(return_value=10)
        pruner = DynamicContextPruner(token_counter=mock_token_counter)

        result = await pruner.prune(
            entries=sample_entries,
            token_budget=0,
        )

        assert result.kept == []
        assert result.pruned_count == len(sample_entries)
        assert result.original_count == len(sample_entries)

    def test_hybrid_scorer_batch_normalizes_recency(
        self, sample_entries: list[MemoryEntry]
    ) -> None:
        """Test HybridScorerImpl.score_batch() normalizes recency to [0, 1]."""
        scorer = HybridScorerImpl(recency_weight=0.6, relevance_weight=0.4)

        # Create entries with different timestamps
        old_entry = sample_entries[2]  # Jan 1
        new_entry = sample_entries[0]  # now (most recent)

        scores = scorer.score_batch([old_entry, new_entry])

        # The newer entry should have a higher recency component
        # Normalize check: the newest should have recency_score = 1.0
        # and oldest should have recency_score = 0.0
        assert len(scores) == 2
        assert scores[1] > scores[0]  # newer entry has higher score
