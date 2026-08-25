"""Pytest configuration for Result pattern tests."""

from unittest.mock import AsyncMock, MagicMock

from _test_rag_cache_support import MockCacheBackend
import pytest

from lexigram.ai.rag.cache import RAGCache, RAGCacheConfig
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


# ── Chunking shared fixtures ────────────────────────────────────────────────
# Used by the test_chunkers_*.py modules.


@pytest.fixture
def chunking_sample_text() -> str:
    """Sample text for testing."""
    return (
        "This is the first sentence. This is the second sentence. "
        "This is the third sentence.\n\n"
        "This is a new paragraph with more content. It has multiple sentences. "
        "Each sentence adds more information.\n\n"
        "Finally, this is the last paragraph. It concludes the document."
    )


@pytest.fixture
def chunking_long_text() -> str:
    """Longer text for testing."""
    return " ".join(list(map(lambda i: f"Sentence number {i}.", range(100))))


# ── RAG cache shared fixtures ───────────────────────────────────────────────
# Used by the test_rag_cache__*.py modules.


@pytest.fixture
def cache() -> RAGCache:
    """Create a cache instance for testing."""
    return RAGCache(backend=MockCacheBackend())


@pytest.fixture
def custom_cache() -> RAGCache:
    """Create a cache with custom config."""
    config = RAGCacheConfig(
        embedding_ttl=100,
        retrieval_ttl=50,
        key_prefix="test:",
    )
    return RAGCache(backend=MockCacheBackend(), config=config)
