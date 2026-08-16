"""Tenant-aware decorators for graph store and graph protocol.

Two strategies:

``GRAPH_PER_TENANT``
    :class:`TenantGraphStoreDecorator` wraps a ``GraphStoreProtocol`` and
    resolves graph names via a ``TenantCollectionResolver`` so each tenant
    gets an isolated named graph.

``NODE_PROPERTY``
    :class:`TenantPropertyFilterGraph` wraps a ``GraphProtocol`` and
    auto-injects ``tenant_id`` into every ``create_node`` / ``create_edge``
    call and every ``find_nodes`` filter.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.data.graph.enums import EdgeDirection
from lexigram.contracts.data.graph.filters import (
    PropertyCondition,
    PropertyConditionGroup,
    PropertyFilter,
    PropertyOperator,
)
from lexigram.contracts.data.graph.tenancy import GraphTenancyStrategy
from lexigram.contracts.data.graph.types import EdgeSpec, NodeSpec
from lexigram.contracts.data.types import LogicalOperator
from lexigram.primitives.context import TENANT_ID, Context

if TYPE_CHECKING:
    from lexigram.contracts.core.health import HealthCheckResult
    from lexigram.contracts.data.graph.protocols import (
        GraphProtocol,
        GraphStoreProtocol,
    )
    from lexigram.contracts.data.graph.types import (
        BulkEdgeResult,
        BulkNodeResult,
        ConstraintSpec,
        EdgeResult,
        GraphEdge,
        GraphInfo,
        GraphNode,
        GraphPath,
        IndexSpec,
        NodeResult,
        TraversalQuery,
    )
    from lexigram.contracts.data.vector.tenancy import TenantCollectionResolver


TENANT_FIELD = "tenant_id"


class TenantGraphStoreDecorator:
    """Wraps a ``GraphStoreProtocol``, auto-resolving graph names from
    the current tenant context.

    ``GRAPH_PER_TENANT`` strategy:
        Templates graph names (``create_graph``, ``get_graph``, ``delete_graph``)
        via the ``TenantCollectionResolver``.

    ``NODE_PROPERTY`` strategy:
        Passes graph names through without template, but wraps every
        ``get_graph()`` result in a ``TenantPropertyFilterGraph`` that
        auto-injects ``tenant_id`` into node/edge queries.

    Lifecycle methods (``connect``, ``disconnect``, ``health_check``) and
    ``list_graphs`` always pass through without modification.
    """

    def __init__(
        self,
        inner: GraphStoreProtocol,
        resolver: TenantCollectionResolver,
        ctx: Context,
        strategy: GraphTenancyStrategy = GraphTenancyStrategy.GRAPH_PER_TENANT,
    ) -> None:
        self._inner = inner
        self._resolver = resolver
        self._ctx = ctx
        self._strategy = strategy

    def _resolve(self, name: str | None) -> str | None:
        if name is None:
            name = "default"
        tenant_id = self._ctx.get(TENANT_ID)
        if tenant_id is None:
            return name if name != "default" else None
        return self._resolver.resolve(name, tenant_id)

    def _tenant_id(self) -> str | None:
        return self._ctx.get(TENANT_ID)

    async def connect(self) -> None:
        await self._inner.connect()

    async def disconnect(self) -> None:
        await self._inner.disconnect()

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        return await self._inner.health_check(timeout)

    async def get_graph(self, name: str | None = None) -> GraphProtocol:
        if self._strategy == GraphTenancyStrategy.NODE_PROPERTY:
            tenant_id = self._tenant_id()
            inner_graph = await self._inner.get_graph(name)
            if tenant_id is None:
                return inner_graph
            return TenantPropertyFilterGraph(inner=inner_graph, tenant_id=tenant_id)
        return await self._inner.get_graph(self._resolve(name))

    async def list_graphs(self) -> list[GraphInfo]:
        return await self._inner.list_graphs()

    async def create_graph(self, name: str) -> None:
        if self._strategy == GraphTenancyStrategy.NODE_PROPERTY:
            await self._inner.create_graph(name)
            return
        resolved = self._resolve(name)
        await self._inner.create_graph(resolved)  # type: ignore[arg-type]

    async def delete_graph(self, name: str) -> None:
        if self._strategy == GraphTenancyStrategy.NODE_PROPERTY:
            await self._inner.delete_graph(name)
            return
        resolved = self._resolve(name)
        await self._inner.delete_graph(resolved)  # type: ignore[arg-type]


class TenantPropertyFilterGraph:
    """Wraps a ``GraphProtocol``, auto-injecting ``tenant_id`` into
    node/edge creation properties and ``find_nodes`` filters
    (``NODE_PROPERTY`` strategy).

    Usage::

        graph = TenantPropertyFilterGraph(inner=neo4j_graph, tenant_id="t1")
        await graph.create_node(labels=["User"], properties={"name": "Alice"})
        # → inner receives properties={"name": "Alice", "tenant_id": "t1"}
    """

    def __init__(self, inner: GraphProtocol, tenant_id: str) -> None:
        self._inner = inner
        self._tenant_id = tenant_id

    def _with_tenant(self, properties: dict[str, Any] | None) -> dict[str, Any]:
        merged = dict(properties or {})
        merged[TENANT_FIELD] = self._tenant_id
        return merged

    def _with_tenant_filter(self, filter: PropertyFilter | None) -> PropertyFilter:
        tenant_condition = PropertyCondition(
            field=TENANT_FIELD,
            operator=PropertyOperator.EQ,
            value=self._tenant_id,
        )
        if filter is None:
            return tenant_condition
        if isinstance(filter, PropertyCondition):
            return PropertyConditionGroup(
                logical_operator=LogicalOperator.AND,
                conditions=(tenant_condition, filter),
            )
        return PropertyConditionGroup(
            logical_operator=LogicalOperator.AND,
            conditions=(tenant_condition, *filter.conditions),
        )

    async def create_node(
        self,
        labels: list[str],
        properties: dict[str, Any] | None = None,
        node_id: str | None = None,
    ) -> NodeResult:
        return await self._inner.create_node(
            labels=labels,
            properties=self._with_tenant(properties),
            node_id=node_id,
        )

    async def get_node(self, node_id: str) -> GraphNode | None:
        return await self._inner.get_node(node_id)

    async def find_nodes(
        self,
        labels: list[str] | None = None,
        filter: PropertyFilter | None = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[GraphNode]:
        return await self._inner.find_nodes(
            labels=labels,
            filter=self._with_tenant_filter(filter),
            limit=limit,
            skip=skip,
        )

    async def update_node(
        self,
        node_id: str,
        properties: dict[str, Any],
        merge: bool = True,
    ) -> bool:
        return await self._inner.update_node(node_id, properties, merge)

    async def delete_node(self, node_id: str, detach: bool = True) -> bool:
        return await self._inner.delete_node(node_id, detach)

    async def neighbors(
        self,
        node_id: str,
        depth: int = 1,
        direction: EdgeDirection | None = None,
        edge_types: list[str] | None = None,
    ) -> list[GraphNode]:
        if direction is None:
            direction = EdgeDirection.BOTH
        return await self._inner.neighbors(
            node_id,
            depth,
            direction,
            edge_types,
        )

    async def count_nodes(self) -> int:
        return await self._inner.count_nodes()

    async def count_edges(self) -> int:
        return await self._inner.count_edges()

    async def get_labels(self) -> list[str]:
        return await self._inner.get_labels()

    async def get_edge_types(self) -> list[str]:
        return await self._inner.get_edge_types()

    async def create_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: str,
        properties: dict[str, Any] | None = None,
    ) -> EdgeResult:
        return await self._inner.create_edge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            properties=self._with_tenant(properties),
        )

    async def get_edge(self, edge_id: str) -> GraphEdge | None:
        return await self._inner.get_edge(edge_id)

    async def get_edges(
        self,
        node_id: str,
        direction: EdgeDirection | None = None,
        edge_types: list[str] | None = None,
        limit: int = 100,
    ) -> list[GraphEdge]:
        if direction is None:
            direction = EdgeDirection.BOTH
        return await self._inner.get_edges(
            node_id,
            direction,
            edge_types,
            limit,
        )

    async def update_edge(
        self,
        edge_id: str,
        properties: dict[str, Any],
        merge: bool = True,
    ) -> bool:
        return await self._inner.update_edge(edge_id, properties, merge)

    async def delete_edge(self, edge_id: str) -> bool:
        return await self._inner.delete_edge(edge_id)

    async def traverse(self, query: TraversalQuery) -> list[GraphPath]:
        return await self._inner.traverse(query)

    async def shortest_path(
        self,
        from_id: str,
        to_id: str,
        max_depth: int = 10,
        edge_types: list[str] | None = None,
        direction: EdgeDirection | None = None,
    ) -> GraphPath | None:
        if direction is None:
            direction = EdgeDirection.BOTH
        return await self._inner.shortest_path(
            from_id,
            to_id,
            max_depth,
            edge_types,
            direction,
        )

    async def query(
        self,
        query_string: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        return await self._inner.query(query_string, parameters)

    async def bulk_create_nodes(self, nodes: list[NodeSpec]) -> BulkNodeResult:
        scoped = [
            NodeSpec(
                labels=n.labels,
                properties=self._with_tenant(n.properties),
                id=n.id,
            )
            for n in nodes
        ]
        return await self._inner.bulk_create_nodes(scoped)

    async def bulk_create_edges(self, edges: list[EdgeSpec]) -> BulkEdgeResult:
        scoped = [
            EdgeSpec(
                source_id=e.source_id,
                target_id=e.target_id,
                type=e.type,
                properties=self._with_tenant(e.properties),
            )
            for e in edges
        ]
        return await self._inner.bulk_create_edges(scoped)

    async def create_index(self, spec: IndexSpec) -> None:
        await self._inner.create_index(spec)

    async def drop_index(self, name: str) -> None:
        await self._inner.drop_index(name)

    async def create_constraint(self, spec: ConstraintSpec) -> None:
        await self._inner.create_constraint(spec)

    async def drop_constraint(self, name: str) -> None:
        await self._inner.drop_constraint(name)


__all__ = ["TenantGraphStoreDecorator", "TenantPropertyFilterGraph"]
