"""Scoring strategies for context pruning."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from lexigram.contracts.ai.memory import MemoryEntry


@runtime_checkable
class RelevanceScorerProtocol(Protocol):
    """Scores a MemoryEntry for pruning priority (higher = keep)."""

    def score(self, entry: MemoryEntry, query: str | None = None) -> float:
        """Score a memory entry for retention.

        Args:
            entry: The memory entry to score.
            query: Optional query context for relevance scoring.

        Returns:
            A score in range [0, 1] or higher, where higher means more important to keep.
        """
        ...


class RecencyScorerImpl:
    """Scores memory entries by recency — more recent entries get higher scores.

    Uses the entry's timestamp to produce a normalized score relative to the
    entire batch of entries being pruned.
    """

    def score(self, entry: MemoryEntry, query: str | None = None) -> float:
        """Score entry by recency.

        Args:
            entry: The memory entry to score.
            query: Optional query (unused by RecencyScorerImpl).

        Returns:
            Score based on entry's timestamp (normalized in batch context).
        """
        ts = getattr(entry, "timestamp", None) or getattr(entry, "created_at", None)
        return ts.timestamp() if ts is not None else 0.0


class HybridScorerImpl:
    """Weighted blend of recency and content length as a proxy for relevance.

    Content length serves as a simple heuristic for information density: longer
    entries are assumed to contain more contextual information.

    Attributes:
        recency_weight: Weight for the recency component (default 0.6).
        relevance_weight: Weight for the content length component (default 0.4).
    """

    def __init__(
        self, recency_weight: float = 0.6, relevance_weight: float = 0.4
    ) -> None:
        """Initialize the hybrid scorer.

        Args:
            recency_weight: Weight for recency in blended score. Default 0.6.
            relevance_weight: Weight for content length (relevance proxy). Default 0.4.
        """
        self._recency_weight = recency_weight
        self._relevance_weight = relevance_weight

    def score_batch(
        self,
        entries: list,
        query: str | None = None,
    ) -> list[float]:
        """Score all entries together, normalizing recency to [0, 1].

        Args:
            entries: List of memory entries to score.
            query: Optional query context (unused by HybridScorerImpl).

        Returns:
            List of scores parallel to the input entries list.
        """
        # Get timestamps (use 0.0 as fallback for missing timestamps)
        timestamps = []
        for entry in entries:
            ts = getattr(entry, "timestamp", None) or getattr(entry, "created_at", None)
            timestamps.append(ts.timestamp() if ts is not None else 0.0)

        min_ts = min(timestamps) if timestamps else 0.0
        max_ts = max(timestamps) if timestamps else 0.0
        ts_range = max_ts - min_ts or 1.0  # avoid division by zero

        scores = []
        for entry, raw_ts in zip(entries, timestamps, strict=True):
            recency_score = (raw_ts - min_ts) / ts_range  # normalized [0, 1]
            length_score = min(
                len(str(getattr(entry, "content", "") or "")) / 1000, 1.0
            )
            scores.append(
                self._recency_weight * recency_score
                + self._relevance_weight * length_score
            )
        return scores

    def score(self, entry: MemoryEntry, query: str | None = None) -> float:
        """Score a single entry (recency not normalized — use score_batch for batches).

        Args:
            entry: The memory entry to score.
            query: Optional query (unused by HybridScorerImpl).

        Returns:
            Weighted score of content length (recency omitted without batch context).
        """
        # Length score: normalize to [0, 1], with 1000 chars = max score
        # Entries with more content are assumed more important
        length_score = min(len(entry.content) / 1000.0, 1.0)

        # Return only relevance component (recency requires batch context)
        return self._relevance_weight * length_score


__all__ = ["HybridScorerImpl", "RecencyScorerImpl", "RelevanceScorerProtocol"]
