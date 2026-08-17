from __future__ import annotations

# Knowledge graph package — canonical re-exports.
from lexigram.ai.rag.knowledge_graph.adapter import GraphStoreAdapter
from lexigram.ai.rag.knowledge_graph.core import (
    GraphRAGIntegration,
    KnowledgeGraph,
    KnowledgeGraphBuilder,
)
from lexigram.ai.rag.knowledge_graph.extractors import (
    EntityExtractor,
    RelationshipExtractor,
)
from lexigram.ai.rag.knowledge_graph.schemas import ExtractionResult
from lexigram.ai.rag.knowledge_graph.types import (
    Entity,
    EntityType,
    GraphPath,
    Relationship,
    RelationshipType,
)

__all__ = [
    "Entity",
    "EntityExtractor",
    "EntityType",
    "ExtractionResult",
    "GraphPath",
    "GraphRAGIntegration",
    "GraphStoreAdapter",
    "KnowledgeGraph",
    "KnowledgeGraphBuilder",
    "Relationship",
    "RelationshipExtractor",
    "RelationshipType",
]
