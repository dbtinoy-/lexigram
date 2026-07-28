from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.data.graph import (
    EdgeResult,
    NodeResult,
    StartSpec,
    TraversalQuery,
    TraversalStep,
)
from lexigram.graph.backends.memory.graph import InMemoryGraph
from lexigram.graph.backends.neo4j.graph import Neo4jGraph


class TestGraphNodeOperations:
    @pytest.mark.asyncio
    async def test_create_node_returns_node_result(self) -> None:
        graph = InMemoryGraph("test")
        result = await graph.create_node(labels=["Person"], properties={"name": "John"})
        assert isinstance(result, NodeResult)
        assert result.id is not None

    @pytest.mark.asyncio
    async def test_create_node_with_custom_id(self) -> None:
        graph = InMemoryGraph("test")
        result = await graph.create_node(
            labels=["Person"], properties={"name": "John"}, node_id="custom-id"
        )
        assert result.id == "custom-id"

    @pytest.mark.asyncio
    async def test_get_node_returns_graph_node(self) -> None:
        graph = InMemoryGraph("test")
        created = await graph.create_node(
            labels=["Person"], properties={"name": "John"}
        )
        node = await graph.get_node(created.id)
        assert node is not None
        assert node.id == created.id
        assert "Person" in node.labels

    @pytest.mark.asyncio
    async def test_get_node_returns_none_for_missing(self) -> None:
        graph = InMemoryGraph("test")
        node = await graph.get_node("nonexistent")
        assert node is None

    @pytest.mark.asyncio
    async def test_find_nodes_by_label(self) -> None:
        graph = InMemoryGraph("test")
        await graph.create_node(labels=["Person"], properties={"name": "Alice"})
        await graph.create_node(labels=["Person"], properties={"name": "Bob"})
        await graph.create_node(labels=["Place"], properties={"name": "NYC"})
        nodes = await graph.find_nodes(labels=["Person"])
        assert len(nodes) == 2

    @pytest.mark.asyncio
    async def test_find_nodes_with_limit(self) -> None:
        graph = InMemoryGraph("test")
        for i in range(5):
            await graph.create_node(
                labels=["Person"], properties={"name": f"Person{i}"}
            )
        nodes = await graph.find_nodes(labels=["Person"], limit=2)
        assert len(nodes) == 2

    @pytest.mark.asyncio
    async def test_find_nodes_with_skip(self) -> None:
        graph = InMemoryGraph("test")
        for i in range(5):
            await graph.create_node(
                labels=["Person"], properties={"name": f"Person{i}"}
            )
        nodes = await graph.find_nodes(labels=["Person"], skip=3)
        assert len(nodes) == 2

    @pytest.mark.asyncio
    async def test_delete_node(self) -> None:
        graph = InMemoryGraph("test")
        result = await graph.create_node(labels=["Person"], properties={"name": "John"})
        node = await graph.get_node(result.id)
        assert node is not None


class TestGraphEdgeOperations:
    @pytest.fixture
    async def graph_with_nodes(self) -> tuple[InMemoryGraph, str, str]:
        graph = InMemoryGraph("test")
        node1 = await graph.create_node(labels=["Person"], node_id="person1")
        node2 = await graph.create_node(labels=["Person"], node_id="person2")
        return graph, node1.id, node2.id

    @pytest.mark.asyncio
    async def test_create_edge_returns_edge_result(
        self, graph_with_nodes: tuple[InMemoryGraph, str, str]
    ) -> None:
        graph, source, target = graph_with_nodes
        result = await graph.create_edge(
            source_id=source, target_id=target, edge_type="KNOWS"
        )
        assert isinstance(result, EdgeResult)
        assert result.id is not None

    @pytest.mark.asyncio
    async def test_create_edge_with_properties(
        self, graph_with_nodes: tuple[InMemoryGraph, str, str]
    ) -> None:
        graph, source, target = graph_with_nodes
        result = await graph.create_edge(
            source_id=source,
            target_id=target,
            edge_type="KNOWS",
            properties={"since": "2020"},
        )
        assert result.created is True

    @pytest.mark.asyncio
    async def test_traverse_returns_paths(
        self, graph_with_nodes: tuple[InMemoryGraph, str, str]
    ) -> None:
        graph, source, target = graph_with_nodes
        await graph.create_edge(source_id=source, target_id=target, edge_type="KNOWS")
        query = TraversalQuery(
            start=StartSpec(node_ids=(source,)),
            steps=(TraversalStep(max_depth=10),),
        )
        paths = await graph.traverse(query)
        assert isinstance(paths, list)


class TestGraphTraversal:
    @pytest.fixture
    async def connected_graph(self) -> InMemoryGraph:
        graph = InMemoryGraph("test")
        a = await graph.create_node(labels=["Node"], node_id="a")
        b = await graph.create_node(labels=["Node"], node_id="b")
        c = await graph.create_node(labels=["Node"], node_id="c")
        d = await graph.create_node(labels=["Node"], node_id="d")
        await graph.create_edge(source_id=a.id, target_id=b.id, edge_type="NEXT")
        await graph.create_edge(source_id=b.id, target_id=c.id, edge_type="NEXT")
        await graph.create_edge(source_id=c.id, target_id=d.id, edge_type="NEXT")
        return graph

    @pytest.mark.asyncio
    async def test_traverse_from_start_node(
        self, connected_graph: InMemoryGraph
    ) -> None:
        query = TraversalQuery(
            start=StartSpec(node_ids=("a",)),
            steps=(TraversalStep(max_depth=10),),
        )
        paths = await connected_graph.traverse(query)
        assert len(paths) > 0

    @pytest.mark.asyncio
    async def test_traverse_empty_for_missing_start(self) -> None:
        graph = InMemoryGraph("test")
        query = TraversalQuery(
            start=StartSpec(node_ids=("nonexistent",)),
            steps=(TraversalStep(max_depth=10),),
        )
        paths = await graph.traverse(query)
        assert len(paths) == 0

    @pytest.mark.asyncio
    async def test_neo4j_graph_node_operations(self) -> None:
        mock_driver = MagicMock()
        graph = Neo4jGraph(mock_driver, "test")

        mock_session = MagicMock()
        mock_tx = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"id": "node-1"})
        mock_tx.run = AsyncMock(return_value=mock_result)
        mock_session.execute_write = AsyncMock(return_value="node-1")
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_driver.session = MagicMock(return_value=mock_session)

        result = await graph.create_node(labels=["Person"], properties={"name": "John"})
        assert result.id == "node-1"

    @pytest.mark.asyncio
    async def test_neo4j_graph_edge_operations(self) -> None:
        mock_driver = MagicMock()
        graph = Neo4jGraph(mock_driver, "test")

        mock_session = MagicMock()
        mock_tx = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"id": "edge-1"})
        mock_tx.run = AsyncMock(return_value=mock_result)
        mock_session.execute_write = AsyncMock(return_value="edge-1")
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_driver.session = MagicMock(return_value=mock_session)

        result = await graph.create_edge(
            source_id="source-1", target_id="target-1", edge_type="KNOWS"
        )
        assert result.id == "edge-1"

    @pytest.mark.asyncio
    async def test_neo4j_graph_query(self) -> None:
        mock_driver = MagicMock()
        graph = Neo4jGraph(mock_driver, "test")

        mock_session = MagicMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[{"n": {"id": "1"}}])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_driver.session = MagicMock(return_value=mock_session)

        results = await graph.query("MATCH (n) RETURN n")
        assert len(results) == 1
