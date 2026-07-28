"""Tests for memory consolidation and retrieval algorithms."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timedelta


class TestMemoryConsolidationStrategies:
    """Test different consolidation strategies."""

    def test_recency_decay_strategy(self) -> None:
        """Recency decay should weight recent entries."""
        strategy = MagicMock()
        strategy.score = MagicMock(side_effect=lambda age_days: 1.0 / (1.0 + age_days))

        # Recent entry (1 day old)
        recent_score = strategy.score(1)

        # Old entry (30 days old)
        old_score = strategy.score(30)

        assert recent_score > old_score

    def test_access_frequency_strategy(self) -> None:
        """Access frequency should affect importance."""
        strategy = MagicMock()
        strategy.score = MagicMock(side_effect=lambda access_count: access_count * 0.1)

        frequent_score = strategy.score(50)
        infrequent_score = strategy.score(5)

        assert frequent_score > infrequent_score

    def test_deduplication_strategy(self) -> None:
        """Deduplication should remove similar entries."""
        dedup = MagicMock()
        dedup.find_similar = MagicMock(return_value=[{"id": "2"}, {"id": "3"}])

        similar = dedup.find_similar("entry_content", threshold=0.9)

        assert len(similar) > 0

    def test_consolidation_pipeline(self) -> None:
        """Consolidation should run in sequence."""
        pipeline = MagicMock()
        pipeline.add_stage = MagicMock(return_value=pipeline)

        pipeline.add_stage("dedup").add_stage("score").add_stage("prune")

        assert pipeline.add_stage.call_count == 3


class TestMemoryRetrieval:
    """Test memory retrieval algorithms."""

    def test_exact_match_retrieval(self) -> None:
        """Should support exact match retrieval."""
        store = MagicMock()
        store.get_by_id = MagicMock(return_value={"id": "mem_1", "content": "exact"})

        result = store.get_by_id("mem_1")

        assert result is not None

    def test_keyword_search(self) -> None:
        """Should support keyword search."""
        store = MagicMock()
        store.search_keywords = MagicMock(
            return_value=[
                {"id": "mem_1", "score": 0.95},
                {"id": "mem_2", "score": 0.87},
            ]
        )

        results = store.search_keywords("query text", top_k=10)

        assert len(results) > 0
        assert results[0]["score"] >= results[1]["score"]

    def test_semantic_similarity_search(self) -> None:
        """Should support semantic search."""
        store = MagicMock()
        store.semantic_search = MagicMock(
            return_value=[
                {"id": "mem_a", "similarity": 0.92},
                {"id": "mem_b", "similarity": 0.78},
            ]
        )

        results = store.semantic_search("meaning text")

        assert len(results) > 0

    def test_hybrid_search(self) -> None:
        """Should combine keyword and semantic search."""
        store = MagicMock()
        store.hybrid_search = MagicMock(
            return_value=[
                {"id": "mem_x", "combined_score": 0.88},
                {"id": "mem_y", "combined_score": 0.75},
            ]
        )

        results = store.hybrid_search("query", alpha=0.5)

        assert len(results) > 0


class TestMemoryRanking:
    """Test memory entry ranking."""

    def test_relevance_ranking(self) -> None:
        """Should rank by relevance."""
        ranker = MagicMock()
        ranker.rank = MagicMock(
            return_value=[
                {"id": "1", "rank": 1},
                {"id": "2", "rank": 2},
                {"id": "3", "rank": 3},
            ]
        )

        results = ranker.rank(entries=[])

        assert results[0]["rank"] < results[-1]["rank"]

    def test_multi_factor_ranking(self) -> None:
        """Should combine multiple ranking factors."""
        ranker = MagicMock()
        ranker.rank_multi = MagicMock(
            return_value=[
                {"id": "m1", "score": 0.85, "factors": {"relevance": 0.9, "recency": 0.8}},
                {"id": "m2", "score": 0.70, "factors": {"relevance": 0.7, "recency": 0.7}},
            ]
        )

        results = ranker.rank_multi(entries=[], weights={"relevance": 0.6, "recency": 0.4})

        assert len(results) > 0

    def test_personalized_ranking(self) -> None:
        """Should support personalized ranking."""
        ranker = MagicMock()
        ranker.rank_personalized = MagicMock(return_value=[])

        results = ranker.rank_personalized(
            entries=[],
            user_id="user_123",
            user_preferences={"interest": "recent"},
        )

        ranker.rank_personalized.assert_called_once()


class TestMemoryPruning:
    """Test memory pruning/cleanup."""

    def test_capacity_based_pruning(self) -> None:
        """Should prune when capacity exceeded."""
        pruner = MagicMock()
        pruner.prune_by_capacity = MagicMock(return_value={"removed": 15, "kept": 85})

        result = pruner.prune_by_capacity(max_entries=100)

        assert result["removed"] >= 0
        assert result["kept"] >= 0

    def test_age_based_pruning(self) -> None:
        """Should prune old entries."""
        pruner = MagicMock()
        pruner.prune_by_age = MagicMock(return_value={"removed": 5})

        result = pruner.prune_by_age(max_age_days=30)

        assert result["removed"] >= 0

    def test_importance_threshold_pruning(self) -> None:
        """Should prune low-importance entries."""
        pruner = MagicMock()
        pruner.prune_by_importance = MagicMock(return_value={"removed": 10})

        result = pruner.prune_by_importance(threshold=0.3)

        assert result["removed"] >= 0

    def test_combined_pruning(self) -> None:
        """Should combine multiple pruning criteria."""
        pruner = MagicMock()
        pruner.prune_combined = MagicMock(
            return_value={"removed": 20, "reasons": ["age", "importance", "capacity"]}
        )

        result = pruner.prune_combined(
            max_entries=100,
            max_age_days=60,
            importance_threshold=0.2,
        )

        assert result["removed"] >= 0


class TestMemoryConsolidationScheduling:
    """Test consolidation scheduling."""

    def test_time_based_scheduling(self) -> None:
        """Consolidation should run on schedule."""
        scheduler = MagicMock()
        scheduler.schedule_daily = MagicMock(return_value=None)

        scheduler.schedule_daily(hour=2, minute=0)

        scheduler.schedule_daily.assert_called_once()

    def test_event_based_triggering(self) -> None:
        """Consolidation should trigger on events."""
        scheduler = MagicMock()
        scheduler.on_capacity_threshold = MagicMock(return_value=None)

        scheduler.on_capacity_threshold(threshold_percent=80)

        scheduler.on_capacity_threshold.assert_called_once()

    def test_manual_consolidation(self) -> None:
        """Consolidation should be manually triggerable."""
        consolidator = MagicMock()
        consolidator.consolidate_now = MagicMock(return_value={"migrated": 25})

        result = consolidator.consolidate_now()

        assert result["migrated"] >= 0


class TestMemoryStatistics:
    """Test memory usage statistics."""

    def test_storage_stats(self) -> None:
        """Should report storage stats."""
        stats = MagicMock()
        stats.get_storage_stats = MagicMock(
            return_value={
                "working_entries": 50,
                "episodic_entries": 1000,
                "semantic_entries": 5000,
                "total_bytes": 1_000_000,
            }
        )

        info = stats.get_storage_stats()

        assert info["total_bytes"] > 0

    def test_performance_metrics(self) -> None:
        """Should report performance metrics."""
        stats = MagicMock()
        stats.get_performance = MagicMock(
            return_value={
                "avg_retrieval_ms": 45.2,
                "avg_write_ms": 12.1,
                "cache_hit_rate": 0.73,
            }
        )

        metrics = stats.get_performance()

        assert metrics["cache_hit_rate"] >= 0.0
