"""Query/traversal tests for ``GraphStoreAdapter``.

Validates that neighbor, relationship, path, subgraph, and stats
operations delegate to the underlying ``GraphProtocol`` and convert
results back to RAG domain types.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram.ai.rag.knowledge_graph.adapter import GraphStoreAdapter
from lexigram.contracts.data.graph.enums import EdgeDirection
from lexigram.contracts.data.graph.types import (
    GraphEdge,
    GraphNode,
    GraphPath as InfraGraphPath,
)
from lexigram.ai.rag.knowledge_graph.types import RelationshipType


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
            "Alice",
            "Bob",
            relationship_types=[RelationshipType.WORKS_AT],
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
