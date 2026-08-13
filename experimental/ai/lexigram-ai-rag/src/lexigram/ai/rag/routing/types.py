"""Core types for query routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from lexigram.ai.rag.multimodal.types import Modality


class QueryIntent(StrEnum):
    """Intent classification for queries.

    Attributes:
        FACTUAL: Questions seeking factual information.
        CONVERSATIONAL: Casual conversation or greetings.
        ANALYTICAL: Queries requiring comparison or analysis.
        CREATIVE: Requests for creative content generation.
        PROCEDURAL: How-to questions or instructions.
        NAVIGATIONAL: Queries seeking specific pages or resources.
    """

    FACTUAL = "factual"
    CONVERSATIONAL = "conversational"
    ANALYTICAL = "analytical"
    CREATIVE = "creative"
    PROCEDURAL = "procedural"
    NAVIGATIONAL = "navigational"


class DataSourceType(StrEnum):
    """Types of data sources for routing.

    Attributes:
        VECTOR_STORE: Dense vector embeddings store.
        KEYWORD_INDEX: Sparse keyword-based index (BM25, TF-IDF).
        KNOWLEDGE_GRAPH: Graph database for structured knowledge.
        SQL_DATABASE: Relational database for structured queries.
        EXTERNAL_API: External API or web service.
        MULTIMODAL_STORE: Multi-modal content store (images, audio, video).
    """

    VECTOR_STORE = "vector_store"
    KEYWORD_INDEX = "keyword_index"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    SQL_DATABASE = "sql_database"
    EXTERNAL_API = "external_api"
    MULTIMODAL_STORE = "multimodal_store"


@dataclass
class QueryFeatures:
    """Features extracted from a query for routing decisions.

    Attributes:
        text: Original query text.
        length: Character count of the query.
        intent: Classified intent of the query.
        language: Detected language code (e.g., 'en', 'es').
        domain: Optional domain classification (e.g., 'technical', 'medical').
        keywords: Extracted keywords from the query.
        has_entities: Whether named entities were detected.
        modalities: Detected modalities (text, image, audio, video).
        complexity: Query complexity score (0-1).
        metadata: Additional metadata for routing decisions.
    """

    text: str
    length: int
    intent: QueryIntent
    language: str = "en"
    domain: str | None = None
    keywords: list[str] = field(default_factory=list)
    has_entities: bool = False
    modalities: list[Modality] = field(default_factory=lambda: [Modality.TEXT])
    complexity: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_simple(self) -> bool:
        """Check if query is simple (low complexity)."""
        return self.complexity < 0.3

    @property
    def is_complex(self) -> bool:
        """Check if query is complex (high complexity)."""
        return self.complexity > 0.7

    @property
    def is_multimodal(self) -> bool:
        """Check if query involves multiple modalities."""
        return len(self.modalities) > 1 or Modality.TEXT not in self.modalities

    @property
    def is_long(self) -> bool:
        """Check if query is long (>200 chars)."""
        return self.length > 200


@dataclass
class DataSource:
    """Represents a data source for query routing.

    Attributes:
        name: Unique identifier for the data source.
        type: Type of data source (vector store, keyword index, etc.).
        description: Human-readable description.
        capabilities: List of supported capabilities.
        priority: Priority for routing (higher = more preferred).
        metadata: Additional metadata about the data source.
    """

    name: str
    type: DataSourceType
    description: str
    capabilities: list[str] = field(default_factory=list)
    priority: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def supports(self, capability: str) -> bool:
        """Check if data source supports a capability.

        Args:
            capability: Capability to check (e.g., 'dense_search').

        Returns:
            True if capability is supported, False otherwise.
        """
        return capability in self.capabilities

    def __hash__(self) -> int:
        """Make DataSourceProtocol hashable for use in sets/dicts."""
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        """Check equality based on name."""
        if not isinstance(other, DataSource):
            return NotImplemented
        return self.name == other.name


@dataclass
class RoutingDecision:
    """Result of a routing decision.

    Attributes:
        query: Original query text.
        data_sources: Selected data sources for the query.
        strategy: Retrieval strategy to use.
        confidence: Confidence score (0-1) in the routing decision.
        reasoning: Human-readable explanation of the decision.
        features: Query features used for routing.
        metadata: Additional metadata about the routing decision.
    """

    query: str
    data_sources: list[DataSource]
    strategy: str
    confidence: float
    reasoning: str
    features: QueryFeatures | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def primary_source(self) -> DataSource | None:
        """Get the primary (first) data source."""
        return self.data_sources[0] if self.data_sources else None

    @property
    def is_confident(self) -> bool:
        """Check if routing decision is confident (>0.7)."""
        return self.confidence > 0.7

    @property
    def is_multimodal(self) -> bool:
        """Check if routing involves multimodal sources."""
        return any(
            source.type == DataSourceType.MULTIMODAL_STORE
            for source in self.data_sources
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert routing decision to dictionary.

        Returns:
            Dictionary representation of the routing decision.
        """
        return {
            "query": self.query,
            "data_sources": [
                {
                    "name": source.name,
                    "type": source.type.value,
                    "description": source.description,
                }
                for source in self.data_sources
            ],
            "strategy": self.strategy,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "features": (
                {
                    "intent": self.features.intent.value,
                    "language": self.features.language,
                    "domain": self.features.domain,
                    "modalities": [m.value for m in self.features.modalities],
                }
                if self.features
                else None
            ),
            "metadata": self.metadata,
        }
