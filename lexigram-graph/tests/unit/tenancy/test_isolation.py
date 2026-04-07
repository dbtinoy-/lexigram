"""Cross-tenant isolation tests for graph tenancy.

Verifies that two tenants operating through the tenant decorators
cannot see each other's data, for both GRAPH_PER_TENANT and
NODE_PROPERTY strategies.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram.primitives.context import TENANT_ID


class TestGraphPerTenantIsolation:
    """Isolation via separate named graphs (GRAPH_PER_TENANT)."""

    @pytest.mark.asyncio
    async def test_tenants_get_separate_graph_instances(self) -> None:
        """Same logical name → different physical graph instances."""
        from lexigram.contracts.data.graph.tenancy import GraphTenancyStrategy
        from lexigram.graph.backends.memory.backend import InMemoryGraphStore
        from lexigram.graph.tenancy.decorator import TenantGraphStoreDecorator
        from lexigram.graph.tenancy.resolver import (
            TemplatedTenantCollectionResolver,
        )

        inner = InMemoryGraphStore()
        await inner.connect()

        resolver = TemplatedTenantCollectionResolver(template="{logical}_t_{tenant}")

        ctx_a = MagicMock()
        ctx_a.get.side_effect = lambda k, d=None: "t_a" if k == TENANT_ID else d
        ctx_b = MagicMock()
        ctx_b.get.side_effect = lambda k, d=None: "t_b" if k == TENANT_ID else d

        store_a = TenantGraphStoreDecorator(
            inner=inner, resolver=resolver, ctx=ctx_a,
            strategy=GraphTenancyStrategy.GRAPH_PER_TENANT,
        )
        store_b = TenantGraphStoreDecorator(
            inner=inner, resolver=resolver, ctx=ctx_b,
            strategy=GraphTenancyStrategy.GRAPH_PER_TENANT,
        )

        # get_graph auto-creates on InMemoryGraphStore;
        # resolves to different names per tenant
        graph_a = await store_a.get_graph("users")
        graph_b = await store_b.get_graph("users")

        # Different underlying graph objects (different resolved names)
        assert graph_a is not graph_b

        # Tenant A writes a node
        await graph_a.create_node(labels=["User"], properties={"name": "Alice"})

        # Tenant B should not see it
        nodes_b = await graph_b.find_nodes(labels=["User"])
        assert len(nodes_b) == 0

        # Tenant A still sees it
        nodes_a = await graph_a.find_nodes(labels=["User"])
        assert len(nodes_a) == 1

        await inner.disconnect()


class TestNodePropertyIsolation:
    """Isolation via tenant_id property injection (NODE_PROPERTY).

    The in-memory backend stores tenant_id in node properties (via the
    decorator), but does not filter on read. Actual read-side isolation
    depends on the backend implementing PropertyFilter (e.g., Neo4j).
    These tests verify that tenant_id is properly stored and that the
    filter is correctly constructed.
    """

    @pytest.mark.asyncio
    async def test_tenant_id_stored_in_properties(self) -> None:
        """Tenant_id is stored in node properties via the decorator."""
        from lexigram.contracts.data.graph.tenancy import GraphTenancyStrategy
        from lexigram.graph.backends.memory.backend import InMemoryGraphStore
        from lexigram.graph.tenancy.decorator import TenantGraphStoreDecorator
        from lexigram.graph.tenancy.resolver import (
            TemplatedTenantCollectionResolver,
        )

        inner = InMemoryGraphStore()
        await inner.connect()

        resolver = TemplatedTenantCollectionResolver()

        ctx_a = MagicMock()
        ctx_a.get.side_effect = lambda k, d=None: "t_a" if k == TENANT_ID else d

        store_a = TenantGraphStoreDecorator(
            inner=inner, resolver=resolver, ctx=ctx_a,
            strategy=GraphTenancyStrategy.NODE_PROPERTY,
        )

        graph = await store_a.get_graph("users")
        result = await graph.create_node(
            labels=["User"], properties={"name": "Alice"}, node_id="a1",
        )

        # Verify tenant_id was stored
        node = await graph.get_node("a1")
        assert node is not None
        assert node.properties.get("tenant_id") == "t_a"
        assert node.properties.get("name") == "Alice"

        await inner.disconnect()

    @pytest.mark.asyncio
    async def test_find_nodes_receives_tenant_filter(self) -> None:
        """Verify the filter constructed by TenantPropertyFilterGraph
        includes a tenant_id condition."""
        from lexigram.graph.tenancy.decorator import TenantPropertyFilterGraph
        from lexigram.contracts.data.graph.filters import PropertyCondition, PropertyOperator
        from lexigram.contracts.data.types import LogicalOperator
        from lexigram.contracts.data.graph.protocols import GraphProtocol

        inner = MagicMock(spec=GraphProtocol)
        graph = TenantPropertyFilterGraph(inner=inner, tenant_id="t_a")

        # Create filtered query
        existing = PropertyCondition(field="active", operator=PropertyOperator.EQ, value=True)
        await graph.find_nodes(labels=["User"], filter=existing)

        call_filter = inner.find_nodes.call_args[1]["filter"]
        assert call_filter.logical_operator == LogicalOperator.AND
        conditions = list(call_filter.conditions)
        assert any(
            c.field == "tenant_id" and c.value == "t_a"
            for c in conditions
        )
