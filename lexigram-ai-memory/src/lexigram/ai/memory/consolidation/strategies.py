"""Consolidation strategies — algorithms for pruning and merging memory entries."""

from __future__ import annotations

from datetime import UTC, datetime
import math

from lexigram.contracts.ai.memory import MemoryEntry
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class RecencyDecayStrategy:
    """Prunes entries whose recency score falls below a threshold.

    Uses an exponential decay model with a configurable half-life.
    """

    def __init__(self, half_life_hours: float = 24.0, threshold: float = 0.05) -> None:
        """Initialise the recency decay strategy.

        Args:
            half_life_hours: Time (h) for importance to halve.
            threshold: Entries with recency below this are pruned.
        """
        self._half_life_s = half_life_hours * 3600.0
        self._threshold = threshold

    def should_prune(self, entry: MemoryEntry) -> bool:
        """Return True if *entry* should be pruned.

        Args:
            entry: Entry to evaluate.

        Returns:
            True if the entry's recency score is below threshold.
        """
        age_s = (datetime.now(UTC) - entry.timestamp).total_seconds()
        recency = math.exp(-math.log(2) * age_s / self._half_life_s)
        return recency < self._threshold

    def filter(
        self, entries: list[MemoryEntry]
    ) -> tuple[list[MemoryEntry], list[MemoryEntry]]:
        """Split entries into (kept, pruned).

        Args:
            entries: Entries to evaluate.

        Returns:
            Tuple of (kept, pruned) entry lists.
        """
        kept: list[MemoryEntry] = []
        pruned: list[MemoryEntry] = []
        for e in entries:
            (pruned if self.should_prune(e) else kept).append(e)
        return kept, pruned


class AccessFrequencyStrategy:
    """Preserves high-importance entries; prunes low-importance stale ones."""

    def __init__(self, importance_threshold: float = 0.1) -> None:
        """Initialise the importance threshold strategy.

        Args:
            importance_threshold: Entries below this value are candidates for pruning.
        """
        self._threshold = importance_threshold

    def should_prune(self, entry: MemoryEntry) -> bool:
        """Return True if *entry* importance is below threshold.

        Args:
            entry: Entry to evaluate.

        Returns:
            True if importance is below threshold.
        """
        return entry.importance < self._threshold

    def filter(
        self, entries: list[MemoryEntry]
    ) -> tuple[list[MemoryEntry], list[MemoryEntry]]:
        """Split entries into (kept, pruned).

        Args:
            entries: Entries to evaluate.

        Returns:
            Tuple of (kept, pruned) entry lists.
        """
        kept: list[MemoryEntry] = []
        pruned: list[MemoryEntry] = []
        for e in entries:
            (pruned if self.should_prune(e) else kept).append(e)
        return kept, pruned


class DeduplicationStrategy:
    """Removes near-duplicate entries based on content similarity.

    Two entries are duplicates if their lowercased content shares more than
    *similarity_threshold* characters of the shorter one (Jaccard-like).
    """

    def __init__(self, similarity_threshold: float = 0.85) -> None:
        """Initialise the deduplication strategy.

        Args:
            similarity_threshold: Jaccard-like overlap above which entries
                are considered duplicates.
        """
        self._threshold = similarity_threshold

    def _tokens(self, text: str) -> set[str]:
        return set(text.lower().split())

    def deduplicate(
        self, entries: list[MemoryEntry]
    ) -> tuple[list[MemoryEntry], list[MemoryEntry]]:
        """Return (unique, duplicates).

        Args:
            entries: Entries to deduplicate.

        Returns:
            Tuple of (unique, duplicate) entry lists.
        """
        unique: list[MemoryEntry] = []
        dupes: list[MemoryEntry] = []
        seen_tokens: list[set[str]] = []

        for entry in entries:
            tokens = self._tokens(entry.content)
            is_dup = False
            for seen in seen_tokens:
                if not tokens or not seen:
                    continue
                intersection = len(tokens & seen)
                union = len(tokens | seen)
                if union > 0 and intersection / union >= self._threshold:
                    is_dup = True
                    break
            if is_dup:
                dupes.append(entry)
            else:
                unique.append(entry)
                seen_tokens.append(tokens)

        return unique, dupes


class TimeDecayStrategy:
    """Exponential decay of memory importance based on entry age.

    The *effective importance* of an entry degrades over time using the formula::

        effective = entry.importance * exp(-0.693 * age_hours / half_life_hours)

    This mirrors radio-isotope half-life: after ``half_life_hours`` the importance
    is exactly half the original value.  After two half-lives it is one quarter,
    and so on.

    Unlike :class:`RecencyDecayStrategy` (which *prunes* entries), this strategy
    *reweights* them — entries are not removed but their importance is updated so
    that downstream retrieval ranks them lower.

    Args:
        half_life_hours: Time after which importance halves.  Default is one week
            (168 h).
        min_importance: Floor value — entries will never be weighted below this.

    Example::

        strategy = TimeDecayStrategy(half_life_hours=72.0)
        updated_entries = strategy.apply(all_entries)
    """

    def __init__(
        self,
        half_life_hours: float = 168.0,
        *,
        min_importance: float = 0.01,
    ) -> None:
        """Initialise the time-decay strategy.

        Args:
            half_life_hours: Hours until importance halves (default 168 = 1 week).
            min_importance: Minimum importance floor after decay.
        """
        if half_life_hours <= 0:
            raise ValueError("half_life_hours must be positive")
        self._half_life_hours = half_life_hours
        self._min_importance = min_importance

    def compute_importance(self, entry: MemoryEntry) -> float:
        """Return the time-decayed importance for *entry*.

        Args:
            entry: Memory entry to evaluate.

        Returns:
            Decayed importance value in the range ``[min_importance, entry.importance]``.
        """
        age_hours = (datetime.now(UTC) - entry.timestamp).total_seconds() / 3600.0
        decayed = entry.importance * math.exp(
            -math.log(2) * age_hours / self._half_life_hours
        )
        return max(decayed, self._min_importance)

    def apply(self, entries: list[MemoryEntry]) -> list[MemoryEntry]:
        """Return entries with importance reweighted by age.

        The original entries are not mutated — new :class:`MemoryEntry` objects
        are returned with updated ``importance`` values.

        Args:
            entries: Memory entries to reweight.

        Returns:
            New list of reweighted entries sorted by descending effective importance.
        """
        reweighted: list[MemoryEntry] = []
        for entry in entries:
            new_importance = self.compute_importance(entry)
            reweighted.append(
                MemoryEntry(
                    id=entry.id,
                    owner_id=entry.owner_id,
                    content=entry.content,
                    role=entry.role,
                    importance=new_importance,
                    timestamp=entry.timestamp,
                    metadata=entry.metadata,
                    embedding=entry.embedding,
                )
            )
        reweighted.sort(key=lambda e: e.importance, reverse=True)
        return reweighted


__all__ = [
    "AccessFrequencyStrategy",
    "DeduplicationStrategy",
    "RecencyDecayStrategy",
    "TimeDecayStrategy",
]
