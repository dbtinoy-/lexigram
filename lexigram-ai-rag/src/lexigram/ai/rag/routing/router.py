"""Main query router for RAG systems."""

from __future__ import annotations

from dataclasses import dataclass, field

from lexigram.ai.rag.routing.analyzer import QueryAnalyzer
from lexigram.ai.rag.routing.strategies.base import RoutingStrategy
from lexigram.ai.rag.routing.strategies.rule_based import RuleBasedRouter
from lexigram.ai.rag.routing.types import (
    DataSource,
    QueryFeatures,
    RoutingDecision,
)


@dataclass
class RoutingStatistics:
    """Statistics for query routing.

    Attributes:
        total_queries: Total number of queries routed.
        by_strategy: Count of queries by strategy.
        by_data_source: Count of queries by data source.
        avg_confidence: Average confidence score.
        high_confidence_count: Number of high-confidence decisions (>0.7).
        low_confidence_count: Number of low-confidence decisions (<0.3).
    """

    total_queries: int = 0
    by_strategy: dict[str, int] = field(default_factory=dict)
    by_data_source: dict[str, int] = field(default_factory=dict)
    avg_confidence: float = 0.0
    high_confidence_count: int = 0
    low_confidence_count: int = 0

    def update(self, decision: RoutingDecision) -> None:
        """Update statistics with a routing decision.

        Args:
            decision: Routing decision to record.
        """
        self.total_queries += 1

        # Track strategy
        self.by_strategy[decision.strategy] = (
            self.by_strategy.get(decision.strategy, 0) + 1
        )

        # Track data sources
        for source in decision.data_sources:
            self.by_data_source[source.name] = (
                self.by_data_source.get(source.name, 0) + 1
            )

        # Update confidence stats
        old_avg = self.avg_confidence
        self.avg_confidence = (
            old_avg * (self.total_queries - 1) + decision.confidence
        ) / self.total_queries

        if decision.confidence > 0.7:
            self.high_confidence_count += 1
        elif decision.confidence < 0.3:
            self.low_confidence_count += 1

    def to_dict(self) -> dict:
        """Convert statistics to dictionary.

        Returns:
            Dictionary representation of statistics.
        """
        return {
            "total_queries": self.total_queries,
            "by_strategy": self.by_strategy,
            "by_data_source": self.by_data_source,
            "avg_confidence": round(self.avg_confidence, 3),
            "high_confidence_count": self.high_confidence_count,
            "low_confidence_count": self.low_confidence_count,
            "high_confidence_rate": round(
                self.high_confidence_count / max(self.total_queries, 1),
                3,
            ),
        }


class QueryRouter:
    """Main query router for RAG systems.

    Orchestrates query analysis and routing to appropriate data sources
    using configurable routing strategies.

    Example:
        ```python
        from lexigram.ai.rag import (
            QueryRouter,
            DataSourceProtocol,
            DataSourceType,
            RuleBasedRouter
        )

        # Create router
        router = QueryRouter(
            analyzer=QueryAnalyzer(),
            strategy=RuleBasedRouter.with_defaults()
        )

        # Register data sources
        router.register_source(DataSourceProtocol(
            name="docs_vector",
            type=DataSourceType.VECTOR_STORE,
            description="Documentation vector store",
            capabilities=["dense_search", "semantic_search"],
            priority=10
        ))

        # Route query
        decision = await router.route("How do I configure authentication?")
        logger.info(f"Route to: {decision.data_sources[0].name}")
        logger.info(f"Strategy: {decision.strategy}")
        logger.info(f"Confidence: {decision.confidence}")

        # Get statistics
        stats = router.get_statistics()
        logger.info(f"Total queries: {stats.total_queries}")
        logger.info(f"Avg confidence: {stats.avg_confidence}")
        ```
    """

    def __init__(
        self,
        *,
        analyzer: QueryAnalyzer | None = None,
        strategy: RoutingStrategy | None = None,
    ):
        """Initialize the query router.

        Args:
            analyzer: Query analyzer for feature extraction.
            strategy: Routing strategy to use.
        """
        self.analyzer = analyzer or QueryAnalyzer()
        self.strategy = strategy or RuleBasedRouter.with_defaults()
        self.data_sources: list[DataSource] = []
        self.statistics = RoutingStatistics()

    def register_source(self, source: DataSource) -> None:
        """Register a data source.

        Args:
            source: Data source to register.
        """
        # Check if source already exists
        existing = list(filter(lambda s: s.name == source.name, self.data_sources))
        if existing:
            # Update existing source
            self.data_sources.remove(existing[0])

        self.data_sources.append(source)

        # Sort by priority (highest first)
        self.data_sources.sort(key=lambda s: s.priority, reverse=True)

    def unregister_source(self, name: str) -> bool:
        """Unregister a data source.

        Args:
            name: Name of the data source to unregister.

        Returns:
            True if source was found and removed, False otherwise.
        """
        initial_count = len(self.data_sources)
        self.data_sources = list(filter(lambda s: s.name != name, self.data_sources))
        return len(self.data_sources) < initial_count

    def get_source(self, name: str) -> DataSource | None:
        """Get a data source by name.

        Args:
            name: Name of the data source.

        Returns:
            Data source if found, None otherwise.
        """
        for source in self.data_sources:
            if source.name == name:
                return source
        return None

    def list_sources(self) -> list[DataSource]:
        """List all registered data sources.

        Returns:
            List of registered data sources.
        """
        return self.data_sources.copy()

    async def route(
        self,
        query: str,
        *,
        features: QueryFeatures | None = None,
    ) -> RoutingDecision:
        """Route a query to appropriate data sources.

        Args:
            query: Query text to route.
            features: Pre-extracted query features (optional).

        Returns:
            Routing decision with selected data sources and strategy.
        """
        # Analyze query if features not provided
        if features is None:
            features = await self.analyzer.analyze(query)

        # Route using strategy
        decision = await self.strategy.route(features, self.data_sources)

        # Update statistics
        self.statistics.update(decision)

        return decision

    async def route_batch(
        self,
        queries: list[str],
    ) -> list[RoutingDecision]:
        """Route multiple queries.

        Args:
            queries: List of query texts to route.

        Returns:
            List of routing decisions.
        """
        decisions = []
        for query in queries:
            decision = await self.route(query)
            decisions.append(decision)
        return decisions

    def get_statistics(self) -> RoutingStatistics:
        """Get routing statistics.

        Returns:
            Current routing statistics.
        """
        return self.statistics

    def reset_statistics(self) -> None:
        """Reset routing statistics."""
        self.statistics = RoutingStatistics()

    def set_strategy(self, strategy: RoutingStrategy) -> None:
        """Set the routing strategy.

        Args:
            strategy: New routing strategy to use.
        """
        self.strategy = strategy

    def set_analyzer(self, analyzer: QueryAnalyzer) -> None:
        """Set the query analyzer.

        Args:
            analyzer: New query analyzer to use.
        """
        self.analyzer = analyzer
