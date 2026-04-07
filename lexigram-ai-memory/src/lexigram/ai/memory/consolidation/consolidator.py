"""Memory consolidator — applies strategies and summarises aged entries."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from lexigram.ai.memory.config import ConsolidationConfig
from lexigram.ai.memory.consolidation.strategies import (
    AccessFrequencyStrategy,
    DeduplicationStrategy,
    RecencyDecayStrategy,
)
from lexigram.contracts.ai.memory import (
    ConsolidationResult,
    MemoryEntry,
)
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = get_logger(__name__)


class MemoryConsolidator:
    """Orchestrates consolidation of a batch of MemoryEntry objects.

    Applies deduplication, recency decay pruning, and importance-floor
    pruning in sequence. Optionally runs a summarisation pass on the
    remaining aged entries.
    """

    def __init__(
        self,
        config: ConsolidationConfig | None = None,
        summarise_fn: Callable[[list[MemoryEntry]], Awaitable[MemoryEntry]]
        | None = None,
    ) -> None:
        """Initialise the consolidator.

        Args:
            config: Consolidation thresholds. Defaults to ``ConsolidationConfig()``.
            summarise_fn: Optional async callable for summarising aged entry groups.
        """
        self._config = config or ConsolidationConfig()
        self._summarise_fn = summarise_fn
        self._dedup = DeduplicationStrategy()
        self._recency = RecencyDecayStrategy(
            half_life_hours=self._config.age_threshold_hours / 2,
        )
        self._importance = AccessFrequencyStrategy(
            importance_threshold=self._config.importance_prune_threshold,
        )

    async def consolidate(self, entries: list[MemoryEntry]) -> ConsolidationResult:
        """Consolidate *entries* via deduplication, decay, and importance pruning.

        Args:
            entries: Entries to process.

        Returns:
            ConsolidationResult with counts of processed, consolidated, pruned,
            and extracted entities.
        """
        start = datetime.now(UTC)
        n = len(entries)

        # Step 1: Deduplication
        unique, dupes = self._dedup.deduplicate(entries)
        pruned_count = len(dupes)

        # Step 2: Recency decay pruning
        after_recency, recency_pruned = self._recency.filter(unique)
        pruned_count += len(recency_pruned)

        # Step 3: Importance pruning
        final_kept, imp_pruned = self._importance.filter(after_recency)
        pruned_count += len(imp_pruned)

        # Step 4: Optional summarisation of surviving large batches
        consolidated_count = 0
        if self._summarise_fn and len(final_kept) > self._config.batch_size:
            batches = [
                final_kept[i : i + self._config.batch_size]
                for i in range(0, len(final_kept), self._config.batch_size)
            ]
            consolidated_count = len(batches)
            for batch in batches:
                await self._summarise_fn(batch)

        elapsed = (datetime.now(UTC) - start).total_seconds() * 1000
        result = ConsolidationResult(
            entries_processed=n,
            entries_consolidated=consolidated_count,
            entries_pruned=pruned_count,
            entities_extracted=0,
            duration_ms=elapsed,
        )
        logger.info(
            "consolidation_complete",
            processed=n,
            pruned=pruned_count,
            consolidated=consolidated_count,
            duration_ms=elapsed,
        )
        return result

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report consolidator health.

        Args:
            timeout: Maximum seconds for the health check.

        Returns:
            HealthCheckResult indicating HEALTHY status.
        """
        return HealthCheckResult(
            component="memory_consolidator",
            status=HealthStatus.HEALTHY,
        )


__all__ = ["MemoryConsolidator"]
