"""Relevance ranker — re-ranks memory search results by combined score."""

from __future__ import annotations

from datetime import UTC, datetime
import math

from lexigram.contracts.ai.memory import MemoryQuery, MemorySearchResult
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class RelevanceRanker:
    """Re-ranks a list of MemorySearchResult by a multi-factor score.

    Combines the raw retrieval score with recency and importance using
    the weights from the originating MemoryQuery.
    """

    def rank(
        self,
        results: list[MemorySearchResult],
        query: MemoryQuery,
    ) -> list[MemorySearchResult]:
        """Re-rank *results* and return a new sorted list.

        Args:
            results: Raw search results to re-rank.
            query: Original query with weighting parameters.

        Returns:
            Results sorted by descending combined score.
        """
        reranked: list[MemorySearchResult] = []
        for r in results:
            age_s = (datetime.now(UTC) - r.entry.timestamp).total_seconds()
            recency = math.exp(-age_s / 86400.0)
            combined = (
                query.relevance_weight * r.score
                + query.recency_weight * recency
                + query.importance_weight * r.entry.importance
            )
            reranked.append(
                MemorySearchResult(entry=r.entry, score=combined, source=r.source)
            )
        reranked.sort(key=lambda x: x.score, reverse=True)
        return reranked

    def top_k(
        self,
        results: list[MemorySearchResult],
        query: MemoryQuery,
        k: int | None = None,
    ) -> list[MemorySearchResult]:
        """Re-rank and return the top *k* results.

        Args:
            results: Raw results to rank.
            query: Query parameters.
            k: Maximum results to return. Defaults to ``query.top_k``.

        Returns:
            Top-k results after re-ranking.
        """
        ranked = self.rank(results, query)
        return ranked[: k or query.top_k]


__all__ = ["RelevanceRanker"]
