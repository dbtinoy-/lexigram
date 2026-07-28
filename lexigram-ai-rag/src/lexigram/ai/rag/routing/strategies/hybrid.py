"""Hybrid routing strategy combining multiple strategies."""

from __future__ import annotations

from lexigram.ai.rag.routing.strategies.base import RoutingStrategy
from lexigram.ai.rag.routing.types import (
    DataSource,
    QueryFeatures,
    RoutingDecision,
)
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class HybridRouter:
    """Hybrid routing strategy combining multiple routers.

    Tries strategies in order until one returns a confident decision,
    or combines results from multiple strategies using ensemble voting.

    Example:
        ```python
        from lexigram.ai.rag import (
            HybridRouter,
            RuleBasedRouter,
            SemanticRouter,
            LLMRouter
        )

        hybrid = HybridRouter(
            strategies=[
                RuleBasedRouter.with_defaults(),
                SemanticRouter.with_defaults(embed_fn=embed),
                LLMRouter(llm_fn=llm),
            ],
            confidence_threshold=0.7,
            use_ensemble=False  # Try in order
        )

        decision = await hybrid.route(features, available_sources)
        ```
    """

    def __init__(
        self,
        *,
        strategies: list[RoutingStrategy] | None = None,
        confidence_threshold: float = 0.7,
        use_ensemble: bool = False,
    ):
        """Initialize the hybrid router.

        Args:
            strategies: List of routing strategies to use.
            confidence_threshold: Confidence threshold for accepting decisions.
            use_ensemble: Whether to use ensemble voting (combine all strategies).
        """
        self.strategies = strategies or []
        self.confidence_threshold = confidence_threshold
        self.use_ensemble = use_ensemble

    def add_strategy(self, strategy: RoutingStrategy) -> None:
        """Add a routing strategy.

        Args:
            strategy: Routing strategy to add.
        """
        self.strategies.append(strategy)

    async def route(
        self,
        features: QueryFeatures,
        available_sources: list[DataSource],
    ) -> RoutingDecision:
        """Route query using hybrid strategy.

        Args:
            features: Extracted query features.
            available_sources: List of available data sources.

        Returns:
            Routing decision from hybrid approach.
        """
        if not self.strategies:
            # No strategies configured, return default
            if available_sources:
                return RoutingDecision(
                    query=features.text,
                    data_sources=[available_sources[0]],
                    strategy="dense",
                    confidence=0.3,
                    reasoning="No routing strategies configured",
                    features=features,
                    metadata={"error": "no_strategies"},
                )
            return RoutingDecision(
                query=features.text,
                data_sources=[],
                strategy="none",
                confidence=0.0,
                reasoning="No strategies or sources available",
                features=features,
                metadata={"error": "no_config"},
            )

        if self.use_ensemble:
            return await self._ensemble_route(features, available_sources)
        return await self._cascade_route(features, available_sources)

    async def _cascade_route(
        self,
        features: QueryFeatures,
        available_sources: list[DataSource],
    ) -> RoutingDecision:
        """Try strategies in order until confident decision.

        Args:
            features: Query features.
            available_sources: Available data sources.

        Returns:
            First confident routing decision.
        """
        last_decision = None

        for strategy in self.strategies:
            decision = await strategy.route(features, available_sources)

            # Return if confident
            if decision.confidence >= self.confidence_threshold:
                decision.metadata["strategy_used"] = strategy.__class__.__name__
                decision.metadata["cascade"] = True
                return decision

            # Keep track of last decision
            last_decision = decision

        # No confident decision, return last one
        if last_decision:
            last_decision.metadata["strategy_used"] = "last_fallback"
            last_decision.metadata["cascade"] = True
            last_decision.reasoning = f"No confident decision (best: {last_decision.confidence:.2f}). {last_decision.reasoning}"
            return last_decision

        # Should not reach here
        return RoutingDecision(
            query=features.text,
            data_sources=[],
            strategy="none",
            confidence=0.0,
            reasoning="No routing decision made",
            features=features,
            metadata={"error": "no_decision"},
        )

    async def _ensemble_route(
        self,
        features: QueryFeatures,
        available_sources: list[DataSource],
    ) -> RoutingDecision:
        """Combine decisions from all strategies using voting.

        Args:
            features: Query features.
            available_sources: Available data sources.

        Returns:
            Ensemble routing decision.
        """
        # Get decisions from all strategies
        decisions = []
        for strategy in self.strategies:
            try:
                decision = await strategy.route(features, available_sources)
                decisions.append(decision)
            except (RuntimeError, ValueError, TypeError, OSError) as e:
                logger.debug(
                    "Strategy %s failed: %s",
                    getattr(strategy, "name", str(strategy)),
                    e,
                )
                # Skip failed strategies
                continue

        if not decisions:
            return RoutingDecision(
                query=features.text,
                data_sources=[],
                strategy="none",
                confidence=0.0,
                reasoning="All strategies failed",
                features=features,
                metadata={"error": "all_failed"},
            )

        # Vote on data sources (weighted by confidence)
        source_votes: dict[str, float] = {}
        strategy_votes: dict[str, float] = {}

        for decision in decisions:
            # Vote for data sources
            for source in decision.data_sources:
                source_votes[source.name] = (
                    source_votes.get(source.name, 0) + decision.confidence
                )

            # Vote for strategy
            strategy_votes[decision.strategy] = (
                strategy_votes.get(decision.strategy, 0) + decision.confidence
            )

        # Select top data sources
        top_sources = sorted(source_votes.items(), key=lambda x: x[1], reverse=True)
        selected_source_names = [x[0] for x in top_sources[:3]]  # Top 3

        selected_sources = [
            source
            for source in available_sources
            if source.name in selected_source_names
        ]

        # Select top strategy
        top_strategy = (
            max(strategy_votes.items(), key=lambda x: x[1])[0]
            if strategy_votes
            else "dense"
        )

        # Calculate ensemble confidence (average of top decisions)
        top_confidences = sorted(
            (d.confidence for d in decisions),
            reverse=True,
        )[:2]
        ensemble_confidence = sum(top_confidences) / len(top_confidences)

        return RoutingDecision(
            query=features.text,
            data_sources=(
                selected_sources or [available_sources[0]] if available_sources else []
            ),
            strategy=top_strategy,
            confidence=ensemble_confidence,
            reasoning=f"Ensemble decision from {len(decisions)} strategies",
            features=features,
            metadata={
                "ensemble": True,
                "num_strategies": len(decisions),
                "source_votes": source_votes,
                "strategy_votes": strategy_votes,
            },
        )
