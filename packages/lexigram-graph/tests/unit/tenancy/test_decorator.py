"""Tests for the tenant-aware graph store and graph decorators."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.data.graph.protocols import (
    GraphProtocol,
    GraphStoreProtocol,
)


@pytest.fixture
def mock_graph() -> MagicMock:
    g = MagicMock(spec=GraphProtocol)
    g.create_node = AsyncMock()
    g.get_node = AsyncMock()
    g.find_nodes = AsyncMock(return_value=[])
    g.update_node = AsyncMock(return_value=True)
    g.delete_node = AsyncMock(return_value=True)
    g.neighbors = AsyncMock(return_value=[])
    g.count_nodes = AsyncMock(return_value=0)
    g.count_edges = AsyncMock(return_value=0)
    g.get_labels = AsyncMock(return_value=[])
    g.get_edge_types = AsyncMock(return_value=[])
    g.create_edge = AsyncMock()
    g.get_edge = AsyncMock()
    g.get_edges = AsyncMock(return_value=[])
    g.update_edge = AsyncMock(return_value=True)
    g.delete_edge = AsyncMock(return_value=True)
    g.traverse = AsyncMock(return_value=[])
    g.shortest_path = AsyncMock()
    g.query = AsyncMock(return_value=[])
    g.bulk_create_nodes = AsyncMock()
    g.bulk_create_edges = AsyncMock()
    g.create_index = AsyncMock()
    g.drop_index = AsyncMock()
    g.create_constraint = AsyncMock()
    g.drop_constraint = AsyncMock()
    return g


@pytest.fixture
def mock_inner_store() -> MagicMock:
    s = MagicMock(spec=GraphStoreProtocol)
    s.connect = AsyncMock()
    s.disconnect = AsyncMock()
    s.health_check = AsyncMock()
    s.get_graph = AsyncMock()
    s.list_graphs = AsyncMock(return_value=[])
    s.create_graph = AsyncMock()
    s.delete_graph = AsyncMock()
    return s


@pytest.fixture
def mock_ctx() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_resolver() -> MagicMock:
    r = MagicMock()
    r.resolve.side_effect = lambda name, tid: f"{name}_t_{tid}"
    return r


class TestTenantGraphStoreDecorator:
    """Tests for the GRAPH_PER_TENANT store decorator."""

    def _make(self, inner, ctx, resolver):
        from lexigram.graph.tenancy.decorator import TenantGraphStoreDecorator
        return TenantGraphStoreDecorator(inner=inner, resolver=resolver, ctx=ctx)

    @pytest.mark.asyncio
    async def test_connect_delegates(self, mock_inner_store, mock_ctx, mock_resolver) -> None:
        d = self._make(mock_inner_store, mock_ctx, mock_resolver)
        await d.connect()
        mock_inner_store.connect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_delegates(self, mock_inner_store, mock_ctx, mock_resolver) -> None:
        d = self._make(mock_inner_store, mock_ctx, mock_resolver)
        await d.disconnect()
        mock_inner_store.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_health_check_delegates(self, mock_inner_store, mock_ctx, mock_resolver) -> None:
        d = self._make(mock_inner_store, mock_ctx, mock_resolver)
        await d.health_check()
        mock_inner_store.health_check.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_graph_resolves_name(self, mock_inner_store, mock_ctx, mock_resolver) -> None:
        mock_ctx.get.return_value = "t1"
        d = self._make(mock_inner_store, mock_ctx, mock_resolver)
        await d.get_graph("my_graph")
        mock_resolver.resolve.assert_called_once_with("my_graph", "t1")
        mock_inner_store.get_graph.assert_awaited_once_with("my_graph_t_t1")

    @pytest.mark.asyncio
    async def test_get_graph_default_when_none(self, mock_inner_store, mock_ctx, mock_resolver) -> None:
        mock_ctx.get.return_value = "t1"
        d = self._make(mock_inner_store, mock_ctx, mock_resolver)
        await d.get_graph()
        mock_resolver.resolve.assert_called_once_with("default", "t1")
        mock_inner_store.get_graph.assert_awaited_once_with("default_t_t1")

    @pytest.mark.asyncio
    async def test_create_graph_resolves_name(self, mock_inner_store, mock_ctx, mock_resolver) -> None:
        mock_ctx.get.return_value = "t1"
        d = self._make(mock_inner_store, mock_ctx, mock_resolver)
        await d.create_graph("my_graph")
        mock_resolver.resolve.assert_called_once_with("my_graph", "t1")
        mock_inner_store.create_graph.assert_awaited_once_with("my_graph_t_t1")

    @pytest.mark.asyncio
    async def test_delete_graph_resolves_name(self, mock_inner_store, mock_ctx, mock_resolver) -> None:
        mock_ctx.get.return_value = "t1"
        d = self._make(mock_inner_store, mock_ctx, mock_resolver)
        await d.delete_graph("my_graph")
        mock_resolver.resolve.assert_called_once_with("my_graph", "t1")
        mock_inner_store.delete_graph.assert_awaited_once_with("my_graph_t_t1")

    @pytest.mark.asyncio
    async def test_list_graphs_passes_through(self, mock_inner_store, mock_ctx, mock_resolver) -> None:
        d = self._make(mock_inner_store, mock_ctx, mock_resolver)
        await d.list_graphs()
        mock_resolver.resolve.assert_not_called()
        mock_inner_store.list_graphs.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_tenant_passes_original_name(self, mock_inner_store, mock_ctx, mock_resolver) -> None:
        mock_ctx.get.return_value = None
        d = self._make(mock_inner_store, mock_ctx, mock_resolver)
        await d.get_graph("my_graph")
        mock_resolver.resolve.assert_not_called()
        mock_inner_store.get_graph.assert_awaited_once_with("my_graph")

    def test_implements_graph_store_protocol(self, mock_inner_store, mock_ctx, mock_resolver) -> None:
        d = self._make(mock_inner_store, mock_ctx, mock_resolver)
        assert isinstance(d, GraphStoreProtocol)


class TestTenantGraphStoreDecoratorNodeProperty:
    """Tests for the store decorator in NODE_PROPERTY strategy mode."""

    def _make(self, inner, ctx, resolver):
        from lexigram.contracts.data.graph.tenancy import GraphTenancyStrategy
        from lexigram.graph.tenancy.decorator import TenantGraphStoreDecorator
        return TenantGraphStoreDecorator(
            inner=inner, resolver=resolver, ctx=ctx,
            strategy=GraphTenancyStrategy.NODE_PROPERTY,
        )

    @pytest.mark.asyncio
    async def test_get_graph_wraps_in_tenant_property_filter(self, mock_inner_store, mock_ctx, mock_resolver) -> None:
        mock_ctx.get.return_value = "t1"
        from lexigram.graph.tenancy.decorator import TenantPropertyFilterGraph
        d = self._make(mock_inner_store, mock_ctx, mock_resolver)
        result = await d.get_graph("my_graph")
        assert isinstance(result, TenantPropertyFilterGraph)
        assert result._tenant_id == "t1"

    @pytest.mark.asyncio
    async def test_get_graph_passes_through_when_no_tenant(self, mock_inner_store, mock_ctx, mock_resolver) -> None:
        mock_ctx.get.return_value = None
        d = self._make(mock_inner_store, mock_ctx, mock_resolver)
        result = await d.get_graph("my_graph")
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_graph_passes_through(self, mock_inner_store, mock_ctx, mock_resolver) -> None:
        d = self._make(mock_inner_store, mock_ctx, mock_resolver)
        await d.create_graph("my_graph")
        mock_inner_store.create_graph.assert_awaited_once_with("my_graph")
        mock_resolver.resolve.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_graph_passes_through(self, mock_inner_store, mock_ctx, mock_resolver) -> None:
        d = self._make(mock_inner_store, mock_ctx, mock_resolver)
        await d.delete_graph("my_graph")
        mock_inner_store.delete_graph.assert_awaited_once_with("my_graph")
        mock_resolver.resolve.assert_not_called()

    @pytest.mark.asyncio
    async def test_connect_delegates(self, mock_inner_store, mock_ctx, mock_resolver) -> None:
        d = self._make(mock_inner_store, mock_ctx, mock_resolver)
        await d.connect()
        mock_inner_store.connect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_graphs_passes_through(self, mock_inner_store, mock_ctx, mock_resolver) -> None:
        d = self._make(mock_inner_store, mock_ctx, mock_resolver)
        await d.list_graphs()
        mock_inner_store.list_graphs.assert_awaited_once()


class TestTenantPropertyFilterGraph:
    """Tests for the NODE_PROPERTY graph decorator."""

    def _make(self, inner, tenant_id: str = "t1"):
        from lexigram.graph.tenancy.decorator import TenantPropertyFilterGraph
        return TenantPropertyFilterGraph(inner=inner, tenant_id=tenant_id)

    @pytest.mark.asyncio
    async def test_create_node_adds_tenant_property(self, mock_graph) -> None:
        d = self._make(mock_graph, "t1")
        await d.create_node(labels=["User"], properties={"name": "Alice"})
        mock_graph.create_node.assert_awaited_once_with(
            labels=["User"], properties={"name": "Alice", "tenant_id": "t1"}, node_id=None,
        )

    @pytest.mark.asyncio
    async def test_create_node_without_properties(self, mock_graph) -> None:
        d = self._make(mock_graph, "t1")
        await d.create_node(labels=["User"])
        mock_graph.create_node.assert_awaited_once_with(
            labels=["User"], properties={"tenant_id": "t1"}, node_id=None,
        )

    @pytest.mark.asyncio
    async def test_create_edge_adds_tenant_property(self, mock_graph) -> None:
        d = self._make(mock_graph, "t1")
        await d.create_edge(source_id="s1", target_id="t1", edge_type="KNOWS", properties={"since": 2024})
        mock_graph.create_edge.assert_awaited_once_with(
            source_id="s1", target_id="t1", edge_type="KNOWS",
            properties={"since": 2024, "tenant_id": "t1"},
        )

    @pytest.mark.asyncio
    async def test_find_nodes_injects_tenant_filter(self, mock_graph) -> None:
        from lexigram.contracts.data.graph.filters import PropertyCondition, PropertyOperator
        d = self._make(mock_graph, "t1")
        existing_filter = PropertyCondition(field="active", operator=PropertyOperator.EQ, value=True)
        await d.find_nodes(labels=["User"], filter=existing_filter)
        call_kwargs = mock_graph.find_nodes.call_args[1]
        called_filter = call_kwargs["filter"]
        assert called_filter is not None
        assert any(
            getattr(c, "field", None) == "tenant_id" or "tenant_id" in str(c)
            for c in called_filter.conditions
        )

    @pytest.mark.asyncio
    async def test_find_nodes_without_filter(self, mock_graph) -> None:
        d = self._make(mock_graph, "t1")
        await d.find_nodes(labels=["User"])
        call_kwargs = mock_graph.find_nodes.call_args[1]
        called_filter = call_kwargs["filter"]
        assert called_filter is not None
        assert called_filter.field == "tenant_id"

    @pytest.mark.asyncio
    async def test_get_node_passes_through(self, mock_graph) -> None:
        d = self._make(mock_graph, "t1")
        await d.get_node("n1")
        mock_graph.get_node.assert_awaited_once_with("n1")

    @pytest.mark.asyncio
    async def test_delete_node_passes_through(self, mock_graph) -> None:
        d = self._make(mock_graph, "t1")
        await d.delete_node("n1")
        mock_graph.delete_node.assert_awaited_once_with("n1", True)

    @pytest.mark.asyncio
    async def test_bulk_create_nodes_adds_tenant_property(self, mock_graph) -> None:
        d = self._make(mock_graph, "t1")
        from lexigram.contracts.data.graph.types import NodeSpec
        nodes = [NodeSpec(labels=["User"], properties={"name": "Alice"})]
        await d.bulk_create_nodes(nodes)
        call_nodes = mock_graph.bulk_create_nodes.call_args[0][0]
        assert call_nodes[0].properties.get("tenant_id") == "t1"

    def test_implements_graph_protocol(self, mock_graph) -> None:
        d = self._make(mock_graph, "t1")
        assert isinstance(d, GraphProtocol)
