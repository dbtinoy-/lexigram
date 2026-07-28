"""Unit tests for consolidation strategies and MemoryConsolidator."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from lexigram.ai.memory.consolidation.consolidator import MemoryConsolidator
from lexigram.ai.memory.consolidation.strategies import (
    AccessFrequencyStrategy,
    DeduplicationStrategy,
    RecencyDecayStrategy,
)
from lexigram.contracts.ai.memory import MemoryEntry

from helpers import make_entry


class TestRecencyDecayStrategy:
    def test_old_entry_pruned(self) -> None:
        strategy = RecencyDecayStrategy(half_life_hours=1.0, threshold=0.5)
        old = MemoryEntry(
            id="old",
            content="old content",
            role="user",
            timestamp=datetime.now(UTC) - timedelta(hours=48),
            importance=0.5,
            metadata={},
        )
        assert strategy.should_prune(old)

    def test_fresh_entry_kept(self) -> None:
        strategy = RecencyDecayStrategy(half_life_hours=24.0, threshold=0.05)
        fresh = make_entry("recent")
        assert not strategy.should_prune(fresh)

    def test_filter_splits_correctly(self) -> None:
        strategy = RecencyDecayStrategy(half_life_hours=1.0, threshold=0.5)
        old = MemoryEntry(
            id="old",
            content="old",
            role="user",
            timestamp=datetime.now(UTC) - timedelta(hours=100),
            importance=0.5,
            metadata={},
        )
        fresh = make_entry("fresh")
        kept, pruned = strategy.filter([fresh, old])
        assert fresh in kept
        assert old in pruned


class TestAccessFrequencyStrategy:
    def test_low_importance_pruned(self) -> None:
        strategy = AccessFrequencyStrategy(importance_threshold=0.3)
        low = make_entry(importance=0.1)
        assert strategy.should_prune(low)

    def test_high_importance_kept(self) -> None:
        strategy = AccessFrequencyStrategy(importance_threshold=0.3)
        high = make_entry(importance=0.9)
        assert not strategy.should_prune(high)


class TestDeduplicationStrategy:
    def test_exact_duplicate_removed(self) -> None:
        strategy = DeduplicationStrategy(similarity_threshold=0.9)
        e1 = make_entry("the quick brown fox jumps over the lazy dog")
        e2 = make_entry("the quick brown fox jumps over the lazy dog")
        unique, dupes = strategy.deduplicate([e1, e2])
        assert len(unique) == 1
        assert len(dupes) == 1

    def test_distinct_entries_kept(self) -> None:
        strategy = DeduplicationStrategy(similarity_threshold=0.9)
        e1 = make_entry("apple orange banana")
        e2 = make_entry("car truck bus train")
        unique, dupes = strategy.deduplicate([e1, e2])
        assert len(unique) == 2
        assert dupes == []


class TestMemoryConsolidator:
    @pytest.mark.asyncio
    async def test_consolidate_empty(self) -> None:
        consolidator = MemoryConsolidator()
        result = await consolidator.consolidate([])
        assert result.entries_processed == 0
        assert result.entries_pruned == 0

    @pytest.mark.asyncio
    async def test_consolidate_prunes_duplicates(self) -> None:
        consolidator = MemoryConsolidator()
        content = "the fox jumps over the lazy dog every single day forever always"
        entries = [make_entry(content) for _ in range(3)]
        result = await consolidator.consolidate(entries)
        assert result.entries_pruned >= 2

    @pytest.mark.asyncio
    async def test_consolidate_returns_result_with_timing(self) -> None:
        consolidator = MemoryConsolidator()
        entries = [make_entry(f"entry {i}") for i in range(5)]
        result = await consolidator.consolidate(entries)
        assert result.entries_processed == 5
        assert result.duration_ms >= 0
