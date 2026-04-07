"""Tests for InMemoryGraph."""

from __future__ import annotations

import pytest

from lexigram.contracts.data.graph import GraphNode, TraversalQuery, StartSpec, TraversalStep
from lexigram.graph.backends.memory import backend, graph as mem_graph


class TestInMemoryGraph:
    """Tests for InMemoryGraph."""

    @pytest.fixture
    def graph(self) -> mem_graph.InMemoryGraph:
        """Create a fresh graph."""
        return mem_graph.InMemoryGraph("test")

    @pytest.mark.asyncio
    async def test_create_node(self, graph: mem_graph.InMemoryGraph) -> None:
        """Verify node creation."""
        result = await graph.create_node(labels=["Person"], properties={"name": "Alice"})
        assert result.id is not None
        node = await graph.get_node(result.id)
        assert node is not None
        assert node.labels == ("Person",)
        assert node.properties["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_create_node_with_id(self, graph: mem_graph.InMemoryGraph) -> None:
        """Verify node creation with explicit ID."""
        result = await graph.create_node(
            labels=["Person"], properties={}, node_id="custom-id"
        )
        assert result.id == "custom-id"
        node = await graph.get_node("custom-id")
        assert node is not None

    @pytest.mark.asyncio
    async def test_get_node_returns_none(self, graph: mem_graph.InMemoryGraph) -> None:
        """Verify get_node returns None for missing node."""
        node = await graph.get_node("missing")
        assert node is None

    @pytest.mark.asyncio
    async def test_find_nodes_all(self, graph: mem_graph.InMemoryGraph) -> None:
        """Verify finding all nodes."""
        await graph.create_node(labels=["Person"], properties={})
        await graph.create_node(labels=["Person"], properties={})
        await graph.create_node(labels=["Place"], properties={})
        results = await graph.find_nodes()
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_find_nodes_by_label(self, graph: mem_graph.InMemoryGraph) -> None:
        """Verify finding nodes by label."""
        await graph.create_node(labels=["Person"], properties={})
        await graph.create_node(labels=["Person"], properties={})
        await graph.create_node(labels=["Place"], properties={})
        results = await graph.find_nodes(labels=["Person"])
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_find_nodes_with_limit(self, graph: mem_graph.InMemoryGraph) -> None:
        """Verify finding nodes with limit."""
        for i in range(10):
            await graph.create_node(labels=["Person"], properties={})
        results = await graph.find_nodes(labels=["Person"], limit=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_find_nodes_with_skip(self, graph: mem_graph.InMemoryGraph) -> None:
        """Verify finding nodes with skip."""
        for i in range(5):
            await graph.create_node(labels=["Person"], properties={})
        results = await graph.find_nodes(labels=["Person"], skip=2)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_create_edge(self, graph: mem_graph.InMemoryGraph) -> None:
        """Verify edge creation."""
        node_a = await graph.create_node(labels=["A"], properties={})
        node_b = await graph.create_node(labels=["B"], properties={})
        result = await graph.create_edge(
            source_id=node_a.id, target_id=node_b.id, edge_type="KNOWS"
        )
        assert result.id is not None
        edges = list(graph._edges.values())
        assert len(edges) == 1
        assert edges[0].source_id == node_a.id
        assert edges[0].target_id == node_b.id
        assert edges[0].type == "KNOWS"

    @pytest.mark.asyncio
    async def test_traverse_finds_paths(self, graph: mem_graph.InMemoryGraph) -> None:
        """Verify traversal finds paths."""
        node_a = await graph.create_node(labels=["Person"], properties={})
        node_b = await graph.create_node(labels=["Person"], properties={})
        node_c = await graph.create_node(labels=["Person"], properties={})
        await graph.create_edge(node_a.id, node_b.id, "KNOWS")
        await graph.create_edge(node_b.id, node_c.id, "KNOWS")

        query = TraversalQuery(
            start=StartSpec(node_ids=(node_a.id,)),
            steps=(TraversalStep(max_depth=2),)
        )
        paths = await graph.traverse(query)
        assert len(paths) == 2

    @pytest.mark.asyncio
    async def test_traverse_no_start_node(self, graph: mem_graph.InMemoryGraph) -> None:
        """Verify traversal with missing start node."""
        query = TraversalQuery(
            start=StartSpec(node_ids=("missing",)),
            steps=(TraversalStep(max_depth=2),)
        )
        paths = await graph.traverse(query)
        assert paths == []

    @pytest.mark.asyncio
    async def test_traverse_filter_by_relationship(
        self, graph: mem_graph.InMemoryGraph
    ) -> None:
        """Verify traversal filters by relationship type."""
        node_a = await graph.create_node(labels=["Person"], properties={})
        node_b = await graph.create_node(labels=["Person"], properties={})
        await graph.create_edge(node_a.id, node_b.id, "KNOWS")

        query = TraversalQuery(
            start=StartSpec(node_ids=(node_a.id,)),
            steps=(TraversalStep(max_depth=2, edge_types=("FOLLOWS",)),)
        )
        paths = await graph.traverse(query)
        assert paths == []

    @pytest.mark.asyncio
    async def test_query_not_implemented(
        self, graph: mem_graph.InMemoryGraph
    ) -> None:
        """Verify query raises not implemented."""
        with pytest.raises(NotImplementedError, match="In-memory does not support Cypher"):
            await graph.query("MATCH (n) RETURN n")

    @pytest.mark.asyncio
    async def test_graph_name(self, graph: mem_graph.InMemoryGraph) -> None:
        """Verify graph name."""
        graph_custom = mem_graph.InMemoryGraph("custom")
        assert graph_custom.name == "custom"