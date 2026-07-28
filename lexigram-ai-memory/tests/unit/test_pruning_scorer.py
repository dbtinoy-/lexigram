"""Unit tests for pruning scorers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from lexigram.ai.memory.pruning.scorer import HybridScorerImpl, RecencyScorerImpl

from helpers import make_entry


class TestRecencyScorerImpl:
    @pytest.mark.asyncio
    async def test_scorer_calculates_recency(self) -> None:
        now = datetime.now(UTC)
        older = make_entry("older", importance=0.5)
        older_ts = type(older)(
            id=older.id,
            content=older.content,
            role=older.role,
            timestamp=now - timedelta(days=1),
            importance=older.importance,
            metadata=older.metadata,
        )
        newer = make_entry("newer", importance=0.5)
        newer_ts = type(newer)(
            id=newer.id,
            content=newer.content,
            role=newer.role,
            timestamp=now,
            importance=newer.importance,
            metadata=newer.metadata,
        )

        scorer = RecencyScorerImpl()
        older_score = scorer.score(older_ts)
        newer_score = scorer.score(newer_ts)

        assert newer_score > older_score

    @pytest.mark.asyncio
    async def test_scorer_handles_empty_entries(self) -> None:
        scorer = RecencyScorerImpl()
        entry = make_entry("test")
        score = scorer.score(entry)
        assert score >= 0.0

    @pytest.mark.asyncio
    async def test_scorer_missing_timestamp_defaults(self) -> None:
        scorer = RecencyScorerImpl()
        entry = make_entry("test", importance=0.5)
        score = scorer.score(entry)
        # When no explicit timestamp is given, created_at defaults to now,
        # so the scorer returns the current epoch time (a large positive float).
        assert score >= 0.0


class TestHybridScorerImpl:
    @pytest.mark.asyncio
    async def test_hybrid_combines_scores(self) -> None:
        entries = [
            make_entry("short"),
            make_entry("much longer content " * 50),
        ]

        scorer = HybridScorerImpl(recency_weight=0.6, relevance_weight=0.4)
        scores = scorer.score_batch(entries)

        assert len(scores) == 2
        assert all(isinstance(s, float) for s in scores)
        assert scores[1] >= scores[0]

    @pytest.mark.asyncio
    async def test_hybrid_respects_weights(self) -> None:
        entries = [make_entry("content " * 100)]

        scorer_high_recency = HybridScorerImpl(recency_weight=0.9, relevance_weight=0.1)
        scorer_high_relevance = HybridScorerImpl(recency_weight=0.1, relevance_weight=0.9)

        scores_high_recency = scorer_high_recency.score_batch(entries)
        scores_high_relevance = scorer_high_relevance.score_batch(entries)

        assert scores_high_recency != scores_high_relevance


class TestRelevanceScorer:
    @pytest.mark.asyncio
    async def test_relevance_scores_by_similarity(self) -> None:
        scorer = HybridScorerImpl(recency_weight=0.0, relevance_weight=1.0)
        low_content = make_entry("a")
        high_content = make_entry("b " * 200)

        low_score = scorer.score(low_content)
        high_score = scorer.score(high_content)

        assert high_score > low_score