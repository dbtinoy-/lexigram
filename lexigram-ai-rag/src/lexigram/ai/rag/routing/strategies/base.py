"""Base routing strategy protocol."""

from __future__ import annotations

from typing import Protocol

from lexigram.ai.rag.routing.types import (
    DataSource,
    QueryFeatures,
    RoutingDecision,
)


class RoutingStrategy(Protocol):
    """Protocol for routing strategies.

    All routing strategies must implement the `route` method that takes
    query features and available data sources, and returns a routing decision.

    Example:
        ```python
        class MyRouter:
            async def route(
                self,
                features: QueryFeatures,
                available_sources: list[DataSourceProtocol]
            ) -> RoutingDecision:
                # Custom routing logic
                return RoutingDecision(...)
        ```
    """

    async def route(
        self,
        features: QueryFeatures,
        available_sources: list[DataSource],
    ) -> RoutingDecision:
        """Route a query to appropriate data sources.

        Args:
            features: Extracted query features.
            available_sources: List of available data sources.

        Returns:
            Routing decision with selected sources and strategy.
        """
        ...
