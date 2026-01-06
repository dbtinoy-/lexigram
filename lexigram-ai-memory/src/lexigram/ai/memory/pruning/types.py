"""Pruning types and enums for context pruning."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class PruningStrategy(StrEnum):
    """Enum of pruning scoring strategies.

    Attributes:
        RECENCY: Keep most recent entries by timestamp.
        RELEVANCE: Keep highest-relevance entries (placeholder for future embedding-based scoring).
        HYBRID: Weighted blend of recency and relevance (content length as proxy).
    """

    RECENCY = "recency"
    RELEVANCE = "relevance"
    HYBRID = "hybrid"


@dataclass(frozen=True)
class PruningResult:
    """Result of a context pruning operation.

    Attributes:
        kept: List of MemoryEntry items kept (score-ordered, highest first).
        pruned_count: Number of entries that were removed.
        original_count: Number of entries that came in.
        token_budget: The token budget that was applied.
        strategy: The pruning strategy used.
        metadata: Optional metadata dictionary with additional pruning details.
    """

    kept: list
    pruned_count: int
    original_count: int
    token_budget: int
    strategy: PruningStrategy
    metadata: dict = field(default_factory=dict)
