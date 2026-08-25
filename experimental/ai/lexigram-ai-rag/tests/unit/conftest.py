"""Pytest configuration for Result pattern tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.rag.knowledge_graph.adapter import GraphStoreAdapter
from lexigram.ai.rag.knowledge_graph.types import (
    Entity,
    EntityType,
    Relationship,
    RelationshipType,
)
from lexigram.contracts.data.graph.types import (
    BulkNodeResult,
    EdgeResult,
    GraphEdge,
    GraphNode,
    NodeResult,
)

try:
    import pytest_asyncio
except ImportError:
    pytest_asyncio = None

if pytest_asyncio:
    pytestmark = pytest.mark.asyncio


# ── GraphStoreAdapter shared fixtures ────────────────────────────────────────
# Used by the test_graph_store_*.py modules.


@pytest.fixture
def mock_graph() -> MagicMock:
    """Mock implementing ``GraphProtocol`` at the contract boundary."""
    graph = MagicMock()
    graph.create_node = AsyncMock(return_value=NodeResult(id="alice", created=True))
    graph.get_node = AsyncMock(return_value=None)
    graph.find_nodes = AsyncMock(return_value=[])
    graph.update_node = AsyncMock(return_value=True)
    graph.bulk_create_nodes = AsyncMock(
        return_value=BulkNodeResult(created_count=1, ids=("alice",))
    )
    graph.create_edge = AsyncMock(return_value=EdgeResult(id="e1", created=True))
    graph.get_edge = AsyncMock(return_value=None)
    graph.get_edges = AsyncMock(return_value=[])
    graph.neighbors = AsyncMock(return_value=[])
    graph.shortest_path = AsyncMock(return_value=None)
    graph.traverse = AsyncMock(return_value=[])
    graph.count_nodes = AsyncMock(return_value=0)
    graph.count_edges = AsyncMock(return_value=0)
    graph.get_labels = AsyncMock(return_value=[])
    graph.get_edge_types = AsyncMock(return_value=[])
    return graph


@pytest.fixture
def adapter(mock_graph: MagicMock) -> GraphStoreAdapter:
    return GraphStoreAdapter(mock_graph)


@pytest.fixture
def alice_entity() -> Entity:
    return Entity(
        name="Alice",
        type=EntityType.PERSON,
        properties={"age": 30},
        metadata={"source": "doc1"},
    )


@pytest.fixture
def alice_node() -> GraphNode:
    return GraphNode(
        id="alice",
        labels=("PERSON",),
        properties={
            "name": "Alice",
            "type": "PERSON",
            "age": 30,
            "__kg_metadata": {"source": "doc1"},
        },
    )


@pytest.fixture
def bob_entity() -> Entity:
    return Entity(name="Bob", type=EntityType.PERSON)


@pytest.fixture
def knows_rel() -> Relationship:
    return Relationship(
        source="Alice",
        target="Bob",
        type=RelationshipType.RELATED_TO,
        confidence=0.9,
        properties={"since": 2020},
        metadata={"extractor": "llm"},
    )


@pytest.fixture
def knows_edge() -> GraphEdge:
    return GraphEdge(
        id="e1",
        type="RELATED_TO",
        source_id="alice",
        target_id="bob",
        properties={
            "confidence": 0.9,
            "_source_name": "Alice",
            "_target_name": "Bob",
            "since": 2020,
            "__kg_metadata": {"extractor": "llm"},
        },
    )
