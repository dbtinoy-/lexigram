"""Dynamic context pruner for token-aware memory management."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.memory.pruning.scorer import HybridScorerImpl, RecencyScorerImpl
from lexigram.ai.memory.pruning.types import PruningResult, PruningStrategy
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.contracts.ai.llm import TokenCounterProtocol
    from lexigram.contracts.ai.memory import MemoryEntry

logger = get_logger(__name__)


class DynamicContextPruner:
    """Prunes MemoryEntry lists to fit within a token budget.

    Uses pluggable scoring strategies to rank entries by importance, then
    greedily selects entries until the token budget is exhausted.

    Attributes:
        token_counter: Protocol for counting tokens in text.
        default_strategy: Default pruning strategy when none is specified.
    """

    def __init__(
        self,
        token_counter: TokenCounterProtocol,
        default_strategy: PruningStrategy = PruningStrategy.HYBRID,
    ) -> None:
        """Initialize the pruner.

        Args:
            token_counter: Implementation of TokenCounterProtocol for token counting.
            default_strategy: Default strategy to use if not overridden. Default is HYBRID.
        """
        self.token_counter = token_counter
        self.default_strategy = default_strategy

    async def prune(
        self,
        entries: list[MemoryEntry],
        token_budget: int,
        query: str | None = None,
        strategy: PruningStrategy | None = None,
        **kwargs,
    ) -> PruningResult:
        """Prune a list of memory entries to fit within a token budget.

        Scores all entries using the specified strategy, sorts them by score
        (descending), then greedily keeps entries until adding the next entry
        would exceed the remaining budget.

        Args:
            entries: List of MemoryEntry objects to prune.
            token_budget: Maximum number of tokens to keep.
            query: Optional query context for relevance-based scoring.
            strategy: Override the default pruning strategy. If None, uses default_strategy.
            **kwargs: Additional keyword arguments (reserved for future use).

        Returns:
            PruningResult containing kept entries (score-ordered), counts,
            and metadata about the pruning operation.
        """
        # Use default strategy if none provided
        selected_strategy = strategy or self.default_strategy

        # Handle empty input
        if not entries:
            return PruningResult(
                kept=[],
                pruned_count=0,
                original_count=0,
                token_budget=token_budget,
                strategy=selected_strategy,
                metadata={},
            )

        # Select scorer based on strategy
        scorer = self._get_scorer(selected_strategy)

        # Score all entries
        if hasattr(scorer, "score_batch"):
            batch_scores = scorer.score_batch(entries, query)
            scored_entries = list(zip(batch_scores, entries, strict=True))
        else:
            scored_entries = [(scorer.score(entry, query), entry) for entry in entries]

        # Sort by score descending (highest scores first)
        scored_entries.sort(key=lambda x: x[0], reverse=True)

        # Greedily select entries until budget is exhausted
        kept: list[MemoryEntry] = []
        remaining_budget = token_budget

        for _score, entry in scored_entries:
            # Count tokens in this entry's content
            entry_tokens = self.token_counter.count(entry.content)

            # Check if entry fits in remaining budget
            if entry_tokens <= remaining_budget:
                kept.append(entry)
                remaining_budget -= entry_tokens
            # If we have no entries yet and this entry exceeds budget,
            # we still add it to avoid returning empty results for single large entries
            elif not kept and token_budget > 0:
                # Force include the first (highest-scored) entry only when budget > 0
                kept.append(entry)
                remaining_budget = 0
                break

        pruned_count = len(entries) - len(kept)

        logger.debug(
            "context_pruned",
            original_count=len(entries),
            kept_count=len(kept),
            pruned_count=pruned_count,
            strategy=selected_strategy,
        )

        return PruningResult(
            kept=kept,
            pruned_count=pruned_count,
            original_count=len(entries),
            token_budget=token_budget,
            strategy=selected_strategy,
            metadata={
                "remaining_budget": remaining_budget,
                "scorer_type": type(scorer).__name__,
            },
        )

    def _get_scorer(self, strategy: PruningStrategy) -> Any:
        """Get the scorer implementation for a given strategy.

        Args:
            strategy: The pruning strategy to use.

        Returns:
            A scorer instance matching the strategy.

        Raises:
            ValueError: If the strategy is not recognized.
        """
        if strategy == PruningStrategy.RELEVANCE:
            logger.warning(
                "pruning_strategy_relevance_not_implemented",
                fallback="recency",
                message="RELEVANCE strategy falls back to RecencyScorerImpl; embedding-based scoring not yet available",
            )

        # Use a registry dict instead of if/elif chains
        scorer_registry = {
            PruningStrategy.RECENCY: RecencyScorerImpl(),
            PruningStrategy.RELEVANCE: RecencyScorerImpl(),  # Same as recency for now
            PruningStrategy.HYBRID: HybridScorerImpl(),
        }

        if strategy not in scorer_registry:
            msg = f"Unknown pruning strategy: {strategy}"
            raise ValueError(msg)

        return scorer_registry[strategy]


__all__ = ["DynamicContextPruner"]
