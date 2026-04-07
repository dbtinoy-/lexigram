"""Rule-based routing strategy."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from lexigram.ai.rag.multimodal.types import Modality
from lexigram.ai.rag.routing.types import (
    DataSource,
    DataSourceType,
    QueryFeatures,
    QueryIntent,
    RoutingDecision,
)


@dataclass
class RoutingRule:
    """A routing rule for rule-based routing.

    Attributes:
        name: Unique identifier for the rule.
        condition: Function that checks if rule applies to query features.
        data_source_types: Preferred data source types when rule matches.
        strategy: Retrieval strategy to use when rule matches.
        priority: Priority of the rule (higher = checked first).
        description: Human-readable description of the rule.
    """

    name: str
    condition: Callable[[QueryFeatures], bool]
    data_source_types: list[DataSourceType]
    strategy: str
    priority: int = 0
    description: str = ""


class RuleBasedRouter:
    """Rule-based routing strategy using if-then rules.

    Routes queries based on configurable rules that match query features
    to appropriate data sources and retrieval strategies.

    Example:
        ```python
        router = RuleBasedRouter.with_defaults()

        # Add custom rule
        router.add_rule(RoutingRule(
            name="multimodal_images",
            condition=lambda f: Modality.IMAGE in f.modalities,
            data_source_types=[DataSourceType.MULTIMODAL_STORE],
            strategy="multimodal",
            priority=10,
            description="Route image queries to multimodal store"
        ))

        # Route query
        decision = await router.route(features, available_sources)
        ```
    """

    def __init__(self) -> None:
        """Initialize the rule-based router with an empty rules list.

        Use `with_defaults()` classmethod to create a router with default rules.
        """
        self.rules: list[RoutingRule] = []

    @classmethod
    def with_defaults(cls) -> RuleBasedRouter:
        """Create a router pre-populated with default routing rules.

        Returns:
            A RuleBasedRouter with all default rules registered.
        """
        instance = cls()
        instance._load_default_rules()
        return instance

    def add_rule(self, rule: RoutingRule) -> None:
        """Add a routing rule.

        Args:
            rule: Routing rule to add.
        """
        self.rules.append(rule)
        # Sort rules by priority (highest first)
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def remove_rule(self, name: str) -> bool:
        """Remove a routing rule by name.

        Args:
            name: Name of the rule to remove.

        Returns:
            True if rule was found and removed, False otherwise.
        """
        initial_count = len(self.rules)
        self.rules = list(filter(lambda r: r.name != name, self.rules))
        return len(self.rules) < initial_count

    async def route(
        self,
        features: QueryFeatures,
        available_sources: list[DataSource],
    ) -> RoutingDecision:
        """Route query using rule-based logic.

        Args:
            features: Extracted query features.
            available_sources: List of available data sources.

        Returns:
            Routing decision based on matched rules.
        """
        # Try each rule in priority order
        for rule in self.rules:
            if rule.condition(features):
                # Find matching data sources
                matching_sources = [
                    source
                    for source in available_sources
                    if source.type in rule.data_source_types
                ]

                if matching_sources:
                    # Sort by priority
                    matching_sources.sort(key=lambda s: s.priority, reverse=True)

                    return RoutingDecision(
                        query=features.text,
                        data_sources=matching_sources,
                        strategy=rule.strategy,
                        confidence=0.9,  # High confidence for rule-based
                        reasoning=f"Matched rule: {rule.description or rule.name}",
                        features=features,
                        metadata={"rule": rule.name},
                    )

        # Fallback: use first available source with default strategy
        if available_sources:
            # Prefer vector stores for general queries
            vector_stores = [
                s for s in available_sources if s.type == DataSourceType.VECTOR_STORE
            ]

            fallback_sources = vector_stores or available_sources
            fallback_sources.sort(key=lambda s: s.priority, reverse=True)

            return RoutingDecision(
                query=features.text,
                data_sources=[fallback_sources[0]],
                strategy="dense_search",
                confidence=0.5,
                reasoning="No matching rules, using default fallback",
                features=features,
                metadata={"fallback": True},
            )

        # No sources available
        return RoutingDecision(
            query=features.text,
            data_sources=[],
            strategy="none",
            confidence=0.0,
            reasoning="No data sources available",
            features=features,
            metadata={"error": "no_sources"},
        )

    def _load_default_rules(self) -> None:
        """Load default routing rules."""

        # Rule 1: Multimodal queries with images
        self.add_rule(
            RoutingRule(
                name="multimodal_image",
                condition=lambda f: Modality.IMAGE in f.modalities,
                data_source_types=[DataSourceType.MULTIMODAL_STORE],
                strategy="multimodal",
                priority=100,
                description="Route image queries to multimodal store",
            ),
        )

        # Rule 2: Multimodal queries with video
        self.add_rule(
            RoutingRule(
                name="multimodal_video",
                condition=lambda f: Modality.VIDEO in f.modalities,
                data_source_types=[DataSourceType.MULTIMODAL_STORE],
                strategy="multimodal",
                priority=95,
                description="Route video queries to multimodal store",
            ),
        )

        # Rule 3: Multimodal queries with audio
        self.add_rule(
            RoutingRule(
                name="multimodal_audio",
                condition=lambda f: Modality.AUDIO in f.modalities,
                data_source_types=[DataSourceType.MULTIMODAL_STORE],
                strategy="multimodal",
                priority=90,
                description="Route audio queries to multimodal store",
            ),
        )

        # Rule 4: Knowledge graph for analytical queries
        self.add_rule(
            RoutingRule(
                name="analytical_graph",
                condition=lambda f: f.intent == QueryIntent.ANALYTICAL,
                data_source_types=[
                    DataSourceType.KNOWLEDGE_GRAPH,
                    DataSourceType.VECTOR_STORE,
                ],
                strategy="hybrid",
                priority=80,
                description="Route analytical queries to knowledge graph + vector store",
            ),
        )

        # Rule 5: Keyword search for navigational queries
        self.add_rule(
            RoutingRule(
                name="navigational_keyword",
                condition=lambda f: f.intent == QueryIntent.NAVIGATIONAL,
                data_source_types=[
                    DataSourceType.KEYWORD_INDEX,
                    DataSourceType.VECTOR_STORE,
                ],
                strategy="sparse",
                priority=70,
                description="Route navigational queries to keyword index",
            ),
        )

        # Rule 6: SQL database for structured queries
        self.add_rule(
            RoutingRule(
                name="structured_sql",
                condition=lambda f: (
                    any(kw in f.keywords for kw in ["count", "total", "average", "sum"])
                    or "data" in f.domain
                    if f.domain
                    else False
                ),
                data_source_types=[
                    DataSourceType.SQL_DATABASE,
                    DataSourceType.VECTOR_STORE,
                ],
                strategy="structured",
                priority=60,
                description="Route structured queries to SQL database",
            ),
        )

        # Rule 7: Keyword-rich queries use sparse retrieval
        self.add_rule(
            RoutingRule(
                name="keyword_rich",
                condition=lambda f: len(f.keywords) > 7,
                data_source_types=[
                    DataSourceType.KEYWORD_INDEX,
                    DataSourceType.VECTOR_STORE,
                ],
                strategy="sparse",
                priority=50,
                description="Route keyword-rich queries to keyword index",
            ),
        )

        # Rule 8: Technical domain prefers vector stores
        self.add_rule(
            RoutingRule(
                name="technical_vector",
                condition=lambda f: f.domain == "technical",
                data_source_types=[DataSourceType.VECTOR_STORE],
                strategy="dense",
                priority=40,
                description="Route technical queries to vector store",
            ),
        )

        # Rule 9: Long queries use dense retrieval
        self.add_rule(
            RoutingRule(
                name="long_dense",
                condition=lambda f: f.is_long,
                data_source_types=[DataSourceType.VECTOR_STORE],
                strategy="dense",
                priority=30,
                description="Route long queries to dense retrieval",
            ),
        )

        # Rule 10: Complex queries use hybrid search
        self.add_rule(
            RoutingRule(
                name="complex_hybrid",
                condition=lambda f: f.is_complex,
                data_source_types=[
                    DataSourceType.VECTOR_STORE,
                    DataSourceType.KEYWORD_INDEX,
                ],
                strategy="hybrid",
                priority=20,
                description="Route complex queries to hybrid search",
            ),
        )

        # Rule 11: Simple factual queries use vector store
        self.add_rule(
            RoutingRule(
                name="simple_factual",
                condition=lambda f: f.intent == QueryIntent.FACTUAL and f.is_simple,
                data_source_types=[DataSourceType.VECTOR_STORE],
                strategy="dense",
                priority=10,
                description="Route simple factual queries to vector store",
            ),
        )
