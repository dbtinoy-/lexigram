"""Semantic routing strategy using embeddings."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from lexigram.ai.rag.routing.types import (
    DataSource,
    DataSourceType,
    QueryFeatures,
    RoutingDecision,
)


@dataclass
class RoutingPattern:
    """A routing pattern for semantic routing.

    Attributes:
        name: Unique identifier for the pattern.
        examples: Example queries that match this pattern.
        data_source_types: Preferred data source types for this pattern.
        strategy: Retrieval strategy to use for this pattern.
        description: Human-readable description.
        embedding: Pre-computed embedding of the pattern (computed from examples).
    """

    name: str
    examples: list[str]
    data_source_types: list[DataSourceType]
    strategy: str
    description: str = ""
    embedding: np.ndarray | None = field(default=None, repr=False)


class SemanticRouter:
    """Semantic routing strategy using embedding similarity.

    Routes queries by comparing query embeddings to pre-defined routing
    patterns and selecting the most similar pattern.

    Example:
        ```python
        from lexigram.ai.rag import SemanticRouter, RoutingPattern

        router = SemanticRouter(embed_fn=my_embed_function)

        # Add routing pattern
        router.add_pattern(RoutingPattern(
            name="technical_docs",
            examples=[
                "How do I configure authentication?",
                "API reference for user management",
                "What are the deployment steps?"
            ],
            data_source_types=[DataSourceType.VECTOR_STORE],
            strategy="dense",
            description="Technical documentation queries"
        ))

        # Route query
        decision = await router.route(features, available_sources)
        ```
    """

    def __init__(
        self,
        *,
        embed_fn: Callable | None = None,
        similarity_threshold: float = 0.7,
    ):
        """Initialize the semantic router.

        Args:
            embed_fn: Function to embed text (async callable).
            similarity_threshold: Minimum similarity for pattern matching.

        Use `with_defaults()` classmethod to create a router with default patterns.
        """
        self.embed_fn = embed_fn
        self.similarity_threshold = similarity_threshold
        self.patterns: list[RoutingPattern] = []

    @classmethod
    def with_defaults(cls, *args, **kwargs) -> SemanticRouter:
        """Create a router pre-populated with default routing patterns.

        Args:
            *args: Positional arguments passed to __init__.
            **kwargs: Keyword arguments passed to __init__.

        Returns:
            A SemanticRouter with all default patterns registered.
        """
        instance = cls(*args, **kwargs)
        instance._load_default_patterns()
        return instance

    async def add_pattern(self, pattern: RoutingPattern) -> None:
        """Add a routing pattern and compute its embedding.

        Args:
            pattern: Routing pattern to add.
        """
        # Compute pattern embedding (average of example embeddings)
        if self.embed_fn and pattern.embedding is None:
            example_embeddings = []
            for example in pattern.examples:
                embedding = await self.embed_fn(example)
                example_embeddings.append(embedding)

            # Average embeddings to create pattern embedding
            pattern.embedding = np.mean(example_embeddings, axis=0)

        self.patterns.append(pattern)

    def remove_pattern(self, name: str) -> bool:
        """Remove a routing pattern by name.

        Args:
            name: Name of the pattern to remove.

        Returns:
            True if pattern was found and removed, False otherwise.
        """
        initial_count = len(self.patterns)
        self.patterns = list(filter(lambda p: p.name != name, self.patterns))
        return len(self.patterns) < initial_count

    async def route(
        self,
        features: QueryFeatures,
        available_sources: list[DataSource],
    ) -> RoutingDecision:
        """Route query using semantic similarity.

        Args:
            features: Extracted query features.
            available_sources: List of available data sources.

        Returns:
            Routing decision based on most similar pattern.
        """
        # Need embedding function to route
        if not self.embed_fn:
            return self._fallback_routing(
                features,
                available_sources,
                "No embedding function configured",
            )

        # Compute query embedding
        try:
            query_embedding = await self.embed_fn(features.text)
        except (ConnectionError, TimeoutError, RuntimeError, ValueError, OSError) as e:
            return self._fallback_routing(
                features,
                available_sources,
                f"Failed to embed query: {e}",
            )

        # Find most similar pattern
        best_pattern = None
        best_similarity = -1.0

        for pattern in self.patterns:
            if pattern.embedding is None:
                continue

            # Compute cosine similarity
            similarity = self._cosine_similarity(query_embedding, pattern.embedding)

            if similarity > best_similarity:
                best_similarity = similarity
                best_pattern = pattern

        # Check if similarity meets threshold
        if best_pattern and best_similarity >= self.similarity_threshold:
            # Find matching data sources
            matching_sources = [
                source
                for source in available_sources
                if source.type in best_pattern.data_source_types
            ]

            if matching_sources:
                matching_sources.sort(key=lambda s: s.priority, reverse=True)

                return RoutingDecision(
                    query=features.text,
                    data_sources=matching_sources,
                    strategy=best_pattern.strategy,
                    confidence=float(best_similarity),
                    reasoning=f"Matched pattern: {best_pattern.description or best_pattern.name} (similarity: {best_similarity:.3f})",
                    features=features,
                    metadata={
                        "pattern": best_pattern.name,
                        "similarity": float(best_similarity),
                    },
                )

        # Fallback if no pattern matched
        return self._fallback_routing(
            features,
            available_sources,
            f"No pattern above threshold {self.similarity_threshold} (best: {best_similarity:.3f})",
        )

    def _fallback_routing(
        self,
        features: QueryFeatures,
        available_sources: list[DataSource],
        reason: str,
    ) -> RoutingDecision:
        """Fallback routing when no pattern matches.

        Args:
            features: Query features.
            available_sources: Available data sources.
            reason: Reason for fallback.

        Returns:
            Fallback routing decision.
        """
        if available_sources:
            # Prefer vector stores
            vector_stores = [
                s for s in available_sources if s.type == DataSourceType.VECTOR_STORE
            ]

            fallback_sources = vector_stores or available_sources
            fallback_sources.sort(key=lambda s: s.priority, reverse=True)

            return RoutingDecision(
                query=features.text,
                data_sources=[fallback_sources[0]],
                strategy="dense",
                confidence=0.3,
                reasoning=f"Fallback routing: {reason}",
                features=features,
                metadata={"fallback": True, "reason": reason},
            )

        return RoutingDecision(
            query=features.text,
            data_sources=[],
            strategy="none",
            confidence=0.0,
            reasoning=f"No sources available: {reason}",
            features=features,
            metadata={"error": "no_sources", "reason": reason},
        )

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            a: First vector.
            b: Second vector.

        Returns:
            Cosine similarity (-1 to 1).
        """
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))

    def _load_default_patterns(self) -> None:
        """Load default routing patterns.

        Note: Embeddings will be computed when embed_fn is available.
        """
        # Pattern 1: Technical documentation
        self.patterns.append(
            RoutingPattern(
                name="technical_docs",
                examples=[
                    "How do I configure authentication?",
                    "API reference for user management",
                    "What are the deployment steps?",
                    "How to setup the database connection?",
                ],
                data_source_types=[DataSourceType.VECTOR_STORE],
                strategy="dense",
                description="Technical documentation queries",
            ),
        )

        # Pattern 2: General Q&A
        self.patterns.append(
            RoutingPattern(
                name="general_qa",
                examples=[
                    "What is the capital of France?",
                    "Who invented the telephone?",
                    "When did World War II end?",
                    "What is photosynthesis?",
                ],
                data_source_types=[DataSourceType.VECTOR_STORE],
                strategy="dense",
                description="General knowledge questions",
            ),
        )

        # Pattern 3: Multi-modal content
        self.patterns.append(
            RoutingPattern(
                name="multimodal_content",
                examples=[
                    "Show me images of sunset beaches",
                    "Find videos about machine learning",
                    "Pictures of classic cars",
                    "Audio recordings of bird songs",
                ],
                data_source_types=[DataSourceType.MULTIMODAL_STORE],
                strategy="multimodal",
                description="Multi-modal content queries",
            ),
        )

        # Pattern 4: Data analysis
        self.patterns.append(
            RoutingPattern(
                name="data_analysis",
                examples=[
                    "What is the average sales by region?",
                    "Count total orders in Q4",
                    "Show revenue trends over time",
                    "Compare performance metrics",
                ],
                data_source_types=[
                    DataSourceType.SQL_DATABASE,
                    DataSourceType.VECTOR_STORE,
                ],
                strategy="structured",
                description="Data analysis and aggregation queries",
            ),
        )

        # Pattern 5: Navigation and search
        self.patterns.append(
            RoutingPattern(
                name="navigation",
                examples=[
                    "Find the pricing page",
                    "Locate documentation for API",
                    "Where is the user guide?",
                    "Link to terms of service",
                ],
                data_source_types=[DataSourceType.KEYWORD_INDEX],
                strategy="sparse",
                description="Navigation and page finding queries",
            ),
        )
