"""Memory retriever — unified retrieval across multiple MemoryStoreProtocol sources."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.memory.retrieval.ranking import RelevanceRanker
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.contracts.ai.memory import (
        MemoryQuery,
        MemorySearchResult,
        MemoryStoreProtocol,
    )

logger = get_logger(__name__)


class MemoryRetriever:
    """Queries one or more MemoryStoreProtocol backends and merges results.

    Results from each backend are pooled, deduplicated by entry ID, and
    re-ranked by the configured RelevanceRanker.  Retrieval counts are
    tracked per entry to enable downstream analytics and relevance decay.
    """

    def __init__(
        self,
        sources: list[MemoryStoreProtocol],
        ranker: RelevanceRanker | None = None,
    ) -> None:
        """Initialise the retriever.

        Args:
            sources: Memory store backends to query in parallel.
            ranker: Optional ranker. Defaults to a new ``RelevanceRanker``.
        """
        self._sources = sources
        self._ranker = ranker or RelevanceRanker()
        self._retrieval_counts: dict[str, int] = {}

    async def retrieve(self, query: MemoryQuery) -> list[MemorySearchResult]:
        """Retrieve and merge results from all configured sources.

        Args:
            query: Search query with weights and filters.

        Returns:
            De-duplicated, re-ranked results capped at ``query.top_k``.
        """
        import asyncio

        tasks = [source.retrieve(query) for source in self._sources]
        all_results_nested = await asyncio.gather(*tasks, return_exceptions=False)

        merged: dict[str, MemorySearchResult] = {}
        for batch in all_results_nested:
            for result in batch:
                # Keep highest raw score if the same entry appears in multiple sources
                existing = merged.get(result.entry.id)
                if existing is None or result.score > existing.score:
                    merged[result.entry.id] = result

        pooled = list(merged.values())
        ranked = self._ranker.top_k(pooled, query)

        # Track retrieval counts for each returned entry
        for result in ranked:
            entry_id = result.entry.id
            self._retrieval_counts[entry_id] = (
                self._retrieval_counts.get(entry_id, 0) + 1
            )

        return ranked

    def add_source(self, source: MemoryStoreProtocol) -> None:
        """Register a new backend source.

        Args:
            source: Additional MemoryStoreProtocol to query.
        """
        self._sources.append(source)

    def get_retrieval_count(self, entry_id: str) -> int:
        """Return how many times a specific entry has been retrieved.

        Args:
            entry_id: The memory entry ID.

        Returns:
            Number of times the entry appeared in retrieval results.
        """
        return self._retrieval_counts.get(entry_id, 0)

    def get_retrieval_stats(self) -> dict[str, Any]:
        """Return aggregate retrieval statistics.

        Returns:
            Dictionary with total retrievals, unique entries, and top-10
            most-retrieved entries.
        """
        total = sum(self._retrieval_counts.values())
        unique = len(self._retrieval_counts)
        sorted_entries = sorted(
            self._retrieval_counts.items(), key=lambda x: x[1], reverse=True
        )
        return {
            "total_retrievals": total,
            "unique_entries": unique,
            "top_entries": sorted_entries[:10],
        }

    def reset_stats(self) -> None:
        """Clear all retrieval tracking data."""
        self._retrieval_counts.clear()


__all__ = ["MemoryRetriever"]
