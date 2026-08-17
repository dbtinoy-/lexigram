"""Tests for ``GraphStoreAdapter``.

Validates that the adapter correctly maps ``Entity``/``Relationship``/``GraphPath``
RAG types to and from the infrastructure ``GraphNode``/``GraphEdge``/``GraphPath``
contracts types, and delegates all operations to the ``GraphProtocol``.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from lexigram.ai.rag.knowledge_graph.adapter import (
    GraphStoreAdapter,
    _entity_to_node_spec,
    _node_to_entity,
    _edge_to_relationship,
    _relationship_to_edge_spec,
    _infra_path_to_rag_path,
)
from lexigram.ai.rag.knowledge_graph.types import (
    Entity,
    EntityType,
    GraphPath,
    Relationship,
    RelationshipType,
)
from lexigram.contracts.data.graph.enums import EdgeDirection
from lexigram.contracts.data.graph.types import (
    EdgeResult,
    GraphEdge,
    GraphNode,
    GraphPath as InfraGraphPath,
    NodeResult,
    BulkNodeResult,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


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


# ── Conversion helper tests ───────────────────────────────────────────────────


class TestEntityNodeConversions:
    """Round-trip mapping Entity ↔ GraphNode."""

    def test_entity_to_node_spec_label(self, alice_entity: Entity) -> None:
        spec = _entity_to_node_spec(alice_entity)
        assert spec.labels == ("PERSON",)

    def test_entity_to_node_spec_id_is_name_lower(
        self, alice_entity: Entity,
    ) -> None:
        spec = _entity_to_node_spec(alice_entity)
        assert spec.id == "alice"

    def test_entity_to_node_spec_properties_include_name(
        self, alice_entity: Entity,
    ) -> None:
        spec = _entity_to_node_spec(alice_entity)
        assert spec.properties["name"] == "Alice"
        assert spec.properties["type"] == "PERSON"
        assert spec.properties["age"] == 30

    def test_entity_to_node_spec_metadata_stored(
        self, alice_entity: Entity,
    ) -> None:
        spec = _entity_to_node_spec(alice_entity)
        assert spec.properties["__kg_metadata"] == {"source": "doc1"}

    def test_node_to_entity_name(self, alice_node: GraphNode) -> None:
        entity = _node_to_entity(alice_node)
        assert entity.name == "Alice"

    def test_node_to_entity_type(self, alice_node: GraphNode) -> None:
        entity = _node_to_entity(alice_node)
        assert entity.type == EntityType.PERSON

    def test_node_to_entity_extra_properties(
        self, alice_node: GraphNode,
    ) -> None:
        entity = _node_to_entity(alice_node)
        assert entity.properties == {"age": 30}

    def test_node_to_entity_metadata_restored(
        self, alice_node: GraphNode,
    ) -> None:
        entity = _node_to_entity(alice_node)
        assert entity.metadata == {"source": "doc1"}

    def test_round_trip_entity_preserves_values(
        self, alice_entity: Entity,
    ) -> None:
        spec = _entity_to_node_spec(alice_entity)
        # Reconstruct a GraphNode from the spec
        node = GraphNode(
            id=spec.id or "",
            labels=spec.labels,
            properties=spec.properties,
        )
        restored = _node_to_entity(node)
        assert restored.name == alice_entity.name
        assert restored.type == alice_entity.type
        assert restored.properties == alice_entity.properties
        assert restored.metadata == alice_entity.metadata


class TestRelationshipEdgeConversions:
    """Round-trip mapping Relationship ↔ GraphEdge."""

    def test_relationship_to_edge_spec_type(
        self, knows_rel: Relationship,
    ) -> None:
        spec = _relationship_to_edge_spec(knows_rel)
        assert spec.type == "RELATED_TO"

    def test_relationship_to_edge_spec_ids_are_lowercased(
        self, knows_rel: Relationship,
    ) -> None:
        spec = _relationship_to_edge_spec(knows_rel)
        assert spec.source_id == "alice"
        assert spec.target_id == "bob"

    def test_relationship_to_edge_spec_confidence(
        self, knows_rel: Relationship,
    ) -> None:
        spec = _relationship_to_edge_spec(knows_rel)
        assert spec.properties["confidence"] == 0.9

    def test_relationship_to_edge_spec_source_target_names(
        self, knows_rel: Relationship,
    ) -> None:
        spec = _relationship_to_edge_spec(knows_rel)
        assert spec.properties["_source_name"] == "Alice"
        assert spec.properties["_target_name"] == "Bob"

    def test_edge_to_relationship_names_restored(
        self, knows_edge: GraphEdge,
    ) -> None:
        rel = _edge_to_relationship(knows_edge)
        assert rel.source == "Alice"
        assert rel.target == "Bob"

    def test_edge_to_relationship_type(self, knows_edge: GraphEdge) -> None:
        rel = _edge_to_relationship(knows_edge)
        assert rel.type == RelationshipType.RELATED_TO

    def test_edge_to_relationship_confidence(
        self, knows_edge: GraphEdge,
    ) -> None:
        rel = _edge_to_relationship(knows_edge)
        assert rel.confidence == 0.9

    def test_edge_to_relationship_extra_properties(
        self, knows_edge: GraphEdge,
    ) -> None:
        rel = _edge_to_relationship(knows_edge)
        assert rel.properties == {"since": 2020}

    def test_edge_to_relationship_metadata_restored(
        self, knows_edge: GraphEdge,
    ) -> None:
        rel = _edge_to_relationship(knows_edge)
        assert rel.metadata == {"extractor": "llm"}


class TestInfraPathConversion:
    """Conversion from infrastructure GraphPath to RAG GraphPath."""

    def test_infra_path_to_rag_path_entity_names(
        self,
        alice_node: GraphNode,
        knows_edge: GraphEdge,
    ) -> None:
        bob_node = GraphNode(
            id="bob",
            labels=("PERSON",),
            properties={"name": "Bob", "type": "PERSON"},
        )
        path = InfraGraphPath(
            nodes=(alice_node, bob_node),
            edges=(knows_edge,),
        )
        rag = _infra_path_to_rag_path(path)
        assert rag.entities == ["Alice", "Bob"]

    def test_infra_path_to_rag_path_length(
        self,
        alice_node: GraphNode,
        knows_edge: GraphEdge,
    ) -> None:
        bob_node = GraphNode(
            id="bob",
            labels=("PERSON",),
            properties={"name": "Bob", "type": "PERSON"},
        )
        path = InfraGraphPath(
            nodes=(alice_node, bob_node),
            edges=(knows_edge,),
        )
        rag = _infra_path_to_rag_path(path)
        assert rag.length == 1

    def test_infra_path_to_rag_path_score_from_confidence(
        self,
        alice_node: GraphNode,
        knows_edge: GraphEdge,
    ) -> None:
        bob_node = GraphNode(
            id="bob",
            labels=("PERSON",),
            properties={"name": "Bob", "type": "PERSON"},
        )
        path = InfraGraphPath(
            nodes=(alice_node, bob_node),
            edges=(knows_edge,),
        )
        rag = _infra_path_to_rag_path(path)
        assert rag.score == pytest.approx(0.9)


# ── Adapter method tests ──────────────────────────────────────────────────────


class TestAddEntity:
    """Adapter.add_entity delegates to GraphProtocol.bulk_create_nodes."""

    @pytest.mark.asyncio
    async def test_add_entity_creates_new_node(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
        alice_entity: Entity,
    ) -> None:
        mock_graph.get_node.return_value = None
        await adapter.add_entity(alice_entity)

        mock_graph.bulk_create_nodes.assert_awaited_once()
        spec = mock_graph.bulk_create_nodes.call_args[0][0][0]
        assert spec.id == "alice"
        assert "PERSON" in spec.labels

    @pytest.mark.asyncio
    async def test_add_entity_upserts_existing_node(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
        alice_entity: Entity,
        alice_node: GraphNode,
    ) -> None:
        mock_graph.get_node.return_value = alice_node
        await adapter.add_entity(alice_entity)

        mock_graph.update_node.assert_awaited_once()
        node_id, kwargs = (
            mock_graph.update_node.call_args[0][0],
            mock_graph.update_node.call_args[1],
        )
        assert node_id == "alice"
        assert kwargs.get("merge") is True


class TestAddRelationship:
    """Adapter.add_relationship delegates to GraphProtocol.create_edge."""

    @pytest.mark.asyncio
    async def test_add_relationship_creates_edge(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
        knows_rel: Relationship,
    ) -> None:
        await adapter.add_relationship(knows_rel)

        mock_graph.create_edge.assert_awaited_once_with(
            source_id="alice",
            target_id="bob",
            edge_type="RELATED_TO",
            properties=mock_graph.create_edge.call_args[1]["properties"],
        )

    @pytest.mark.asyncio
    async def test_add_relationship_logs_warning_on_missing_node(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
        knows_rel: Relationship,
    ) -> None:
        """If source/target node is missing, skip silently with a warning."""
        mock_graph.create_edge.side_effect = RuntimeError("node not found")
        # Should not raise — missing relationships are warned and skipped.
        await adapter.add_relationship(knows_rel)


class TestGetEntity:
    """Adapter.get_entity delegates to GraphProtocol.get_node."""

    @pytest.mark.asyncio
    async def test_get_entity_returns_entity_when_found(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
        alice_node: GraphNode,
    ) -> None:
        mock_graph.get_node.return_value = alice_node
        entity = await adapter.get_entity("Alice")

        mock_graph.get_node.assert_awaited_once_with("alice")
        assert entity is not None
        assert entity.name == "Alice"

    @pytest.mark.asyncio
    async def test_get_entity_returns_none_when_missing(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
    ) -> None:
        mock_graph.get_node.return_value = None
        entity = await adapter.get_entity("Nonexistent")
        assert entity is None


class TestGetAllEntities:
    """Adapter.get_all_entities delegates to GraphProtocol.find_nodes."""

    @pytest.mark.asyncio
    async def test_get_all_entities_converts_nodes(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
        alice_node: GraphNode,
    ) -> None:
        mock_graph.find_nodes.return_value = [alice_node]
        entities = await adapter.get_all_entities()

        assert len(entities) == 1
        assert entities[0].name == "Alice"

    @pytest.mark.asyncio
    async def test_get_all_entities_empty_graph(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
    ) -> None:
        mock_graph.find_nodes.return_value = []
        entities = await adapter.get_all_entities()
        assert entities == []


class TestGetEntitiesByType:
    """Adapter.get_entities_by_type filters by label."""

    @pytest.mark.asyncio
    async def test_get_entities_by_type_calls_find_nodes_with_label(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
        alice_node: GraphNode,
    ) -> None:
        mock_graph.find_nodes.return_value = [alice_node]
        entities = await adapter.get_entities_by_type(EntityType.PERSON)

        mock_graph.find_nodes.assert_awaited_once_with(
            labels=["PERSON"], limit=10_000,
        )
        assert len(entities) == 1


class TestGetNeighbors:
    """Adapter.get_neighbors delegates to GraphProtocol.neighbors."""

    @pytest.mark.asyncio
    async def test_get_neighbors_outgoing(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
        alice_node: GraphNode,
    ) -> None:
        bob_node = GraphNode(
            id="bob",
            labels=("PERSON",),
            properties={"name": "Bob", "type": "PERSON"},
        )
        mock_graph.neighbors.return_value = [bob_node]
        neighbors = await adapter.get_neighbors("Alice", direction="outgoing")

        mock_graph.neighbors.assert_awaited_once_with(
            node_id="alice",
            depth=1,
            direction=EdgeDirection.OUTGOING,
        )
        assert len(neighbors) == 1
        assert neighbors[0].name == "Bob"

    @pytest.mark.asyncio
    async def test_get_neighbors_direction_both(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
    ) -> None:
        mock_graph.neighbors.return_value = []
        await adapter.get_neighbors("Alice", direction="both")
        mock_graph.neighbors.assert_awaited_once_with(
            node_id="alice",
            depth=1,
            direction=EdgeDirection.BOTH,
        )


class TestGetRelationships:
    """Adapter.get_relationships delegates to GraphProtocol.get_edges."""

    @pytest.mark.asyncio
    async def test_get_relationships_returns_mapped_edges(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
        knows_edge: GraphEdge,
    ) -> None:
        mock_graph.get_edges.return_value = [knows_edge]
        rels = await adapter.get_relationships("Alice", direction="outgoing")

        mock_graph.get_edges.assert_awaited_once_with(
            node_id="alice",
            direction=EdgeDirection.OUTGOING,
            limit=10_000,
        )
        assert len(rels) == 1
        assert rels[0].source == "Alice"
        assert rels[0].target == "Bob"


class TestFindPath:
    """Adapter.find_path delegates to GraphProtocol.shortest_path."""

    @pytest.mark.asyncio
    async def test_find_path_returns_rag_graph_path(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
        alice_node: GraphNode,
        knows_edge: GraphEdge,
    ) -> None:
        bob_node = GraphNode(
            id="bob",
            labels=("PERSON",),
            properties={"name": "Bob", "type": "PERSON"},
        )
        infra_path = InfraGraphPath(
            nodes=(alice_node, bob_node),
            edges=(knows_edge,),
        )
        mock_graph.shortest_path.return_value = infra_path
        path = await adapter.find_path("Alice", "Bob", max_depth=5)

        mock_graph.shortest_path.assert_awaited_once_with(
            from_id="alice",
            to_id="bob",
            max_depth=5,
            edge_types=None,
            direction=EdgeDirection.BOTH,
        )
        assert path is not None
        assert path.entities == ["Alice", "Bob"]
        assert path.length == 1

    @pytest.mark.asyncio
    async def test_find_path_returns_none_when_no_path(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
    ) -> None:
        mock_graph.shortest_path.return_value = None
        path = await adapter.find_path("Alice", "Bob")
        assert path is None

    @pytest.mark.asyncio
    async def test_find_path_passes_edge_type_filter(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
    ) -> None:
        mock_graph.shortest_path.return_value = None
        await adapter.find_path(
            "Alice", "Bob", relationship_types=[RelationshipType.WORKS_AT],
        )
        call_kwargs = mock_graph.shortest_path.call_args[1]
        assert call_kwargs["edge_types"] == ["WORKS_AT"]


class TestQuerySubgraph:
    """Adapter.query_subgraph explores BFS to desired depth."""

    @pytest.mark.asyncio
    async def test_query_subgraph_returns_empty_when_root_missing(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
    ) -> None:
        mock_graph.get_node.return_value = None
        entities, rels = await adapter.query_subgraph("Unknown", depth=2)
        assert entities == []
        assert rels == []

    @pytest.mark.asyncio
    async def test_query_subgraph_includes_root_entity(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
        alice_node: GraphNode,
    ) -> None:
        mock_graph.get_node.return_value = alice_node
        mock_graph.get_edges.return_value = []
        entities, rels = await adapter.query_subgraph("Alice", depth=1)

        assert len(entities) == 1
        assert entities[0].name == "Alice"

    @pytest.mark.asyncio
    async def test_query_subgraph_includes_neighbors(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
        alice_node: GraphNode,
        knows_edge: GraphEdge,
    ) -> None:
        bob_node = GraphNode(
            id="bob",
            labels=("PERSON",),
            properties={"name": "Bob", "type": "PERSON"},
        )
        # First call: root node (alice); second call: neighbor (bob)
        mock_graph.get_node.side_effect = [alice_node, bob_node]
        mock_graph.get_edges.return_value = [knows_edge]
        entities, rels = await adapter.query_subgraph("Alice", depth=1)

        entity_names = {e.name for e in entities}
        assert "Alice" in entity_names
        assert "Bob" in entity_names
        assert len(rels) == 1


class TestGetStats:
    """Adapter.get_stats returns counts from GraphProtocol."""

    @pytest.mark.asyncio
    async def test_get_stats_returns_counts(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
    ) -> None:
        mock_graph.count_nodes.return_value = 5
        mock_graph.count_edges.return_value = 3
        mock_graph.get_labels.return_value = ["PERSON", "COMPANY"]
        mock_graph.get_edge_types.return_value = ["KNOWS"]

        stats = await adapter.get_stats()

        assert stats["total_entities"] == 5
        assert stats["total_relationships"] == 3
        assert "PERSON" in stats["entity_types"]


class TestAddEntities:
    """Adapter.add_entities processes a list."""

    @pytest.mark.asyncio
    async def test_add_entities_calls_add_for_each(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
        alice_entity: Entity,
        bob_entity: Entity,
    ) -> None:
        mock_graph.get_node.return_value = None
        await adapter.add_entities([alice_entity, bob_entity])
        assert mock_graph.bulk_create_nodes.await_count == 2


class TestAddRelationships:
    """Adapter.add_relationships processes a list."""

    @pytest.mark.asyncio
    async def test_add_relationships_calls_add_for_each(
        self,
        adapter: GraphStoreAdapter,
        mock_graph: MagicMock,
        knows_rel: Relationship,
    ) -> None:
        await adapter.add_relationships([knows_rel, knows_rel])
        assert mock_graph.create_edge.await_count == 2
