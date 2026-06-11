"""Memory pruner — removes stale or low-relevance entries from memory stores."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.contracts.ai.memory import MemoryStoreProtocol

logger = get_logger(__name__)


@dataclass
class PruneResult:
    """Outcome of a prune operation.

    Attributes:
        pruned_count: Number of entries removed.
        remaining_count: Number of entries kept.
        metadata: Extra details about the prune pass.
    """

    pruned_count: int
    remaining_count: int
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pruned_count": self.pruned_count,
            "remaining_count": self.remaining_count,
            "metadata": self.metadata,
        }


class MemoryPruner:
    """Removes stale or low-relevance entries from a memory store.

    Supports two complementary criteria:

    * **Age-based**: entries older than ``max_age_hours`` are pruned.
    * **Threshold-based**: entries whose ``importance`` score falls below
      ``importance_threshold`` are pruned.

    Both criteria can be combined — an entry is pruned if it matches
    *either* condition.

    Example::

        pruner = MemoryPruner(store)
        result = await pruner.prune(
            importance_threshold=0.2,
            max_age_hours=72,
        )
        print(f"Pruned {result.pruned_count} entries")

    Args:
        store: Memory store to prune entries from.
    """

    def __init__(self, store: MemoryStoreProtocol) -> None:
        """Initialise the pruner.

        Args:
            store: The target memory store backend.
        """
        self._store = store

    async def prune(
        self,
        owner_id: str,
        importance_threshold: float = 0.1,
        max_age_hours: float = 0.0,
        dry_run: bool = False,
    ) -> PruneResult:
        """Prune entries that fall below the given thresholds.

        An entry is eligible for pruning if it matches *either* condition:
        - ``importance < importance_threshold``
        - ``age > max_age_hours`` (if ``max_age_hours > 0``)

        Args:
            owner_id: Owner scope restricting pruning to one owner's entries.
            importance_threshold: Prune entries below this importance score.
            max_age_hours: Prune entries older than this (0 = disabled).
            dry_run: If ``True``, report what would be pruned without deleting.

        Returns:
            ``PruneResult`` with counts and metadata.
        """
        from lexigram.contracts.ai.memory import MemoryQuery

        # Retrieve all entries with a broad query
        all_results = await self._store.retrieve(
            MemoryQuery(
                owner_id=owner_id,
                query="",
                top_k=10_000,
                recency_weight=0.0,
                importance_weight=0.0,
                relevance_weight=1.0,
            )
        )

        now = datetime.now(UTC)
        to_prune: list[str] = []
        age_pruned = 0
        importance_pruned = 0

        for result in all_results:
            entry = result.entry
            prune_this = False

            # Age check
            if max_age_hours > 0:
                age_hours = (now - entry.timestamp).total_seconds() / 3600
                if age_hours > max_age_hours:
                    prune_this = True
                    age_pruned += 1

            # Importance check
            if entry.importance < importance_threshold:
                prune_this = True
                importance_pruned += 1

            if prune_this:
                to_prune.append(entry.id)

        if not dry_run and to_prune:
            for entry_id in to_prune:
                await self._store.delete(entry_id, owner_id)

        remaining = len(all_results) - len(to_prune)

        logger.info(
            "memory_pruned",
            pruned=len(to_prune),
            remaining=remaining,
            dry_run=dry_run,
            age_pruned=age_pruned,
            importance_pruned=importance_pruned,
        )

        return PruneResult(
            pruned_count=len(to_prune),
            remaining_count=remaining,
            metadata={
                "importance_threshold": importance_threshold,
                "max_age_hours": max_age_hours,
                "dry_run": dry_run,
                "age_pruned": age_pruned,
                "importance_pruned": importance_pruned,
            },
        )


__all__ = ["MemoryPruner", "PruneResult"]
