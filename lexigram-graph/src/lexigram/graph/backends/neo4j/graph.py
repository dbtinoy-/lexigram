"""Neo4j graph implementation (Cypher-based)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.data.graph import (
    EdgeResult,
    GraphEdge,
    GraphNode,
    GraphPath,
    NodeResult,
    TraversalQuery,
)
from lexigram.graph.backends.base import BaseGraph

if TYPE_CHECKING:
    from neo4j import (  # type: ignore[import-not-found]
        AsyncDriver,
        AsyncManagedTransaction,
    )

    from lexigram.contracts.data.graph.filters import PropertyFilter


class Neo4jGraph(BaseGraph):
    """Neo4j graph implementation (Cypher-based)."""

    def __init__(self, driver: AsyncDriver, name: str | None = None) -> None:
        super().__init__(name)
        self._driver = driver
        self._database = name or "neo4j"

    async def create_node(
        self,
        labels: list[str],
        properties: dict[str, Any] | None = None,
        node_id: str | None = None,
    ) -> NodeResult:
        """Create a node in Neo4j.

        Args:
            labels: Node labels.
            properties: Optional property map.
            node_id: Optional explicit node ID; stored as the ``id`` property.

        Returns:
            :class:`~lexigram.contracts.data.graph.NodeResult` with the node ID.

        """
        label_str = ":".join(labels)
        props = properties or {}
        if node_id:
            props["id"] = node_id

        cypher = f"CREATE (n:{label_str} $props) RETURN n.id as id"

        async def _work(tx: AsyncManagedTransaction) -> Any:
            result = await tx.run(cypher, props=props)
            record = await result.single()
            return record["id"] if record else node_id

        async with self._driver.session(database=self._database) as session:
            nid = await session.execute_write(_work)
            return NodeResult(id=nid)

    async def get_node(self, node_id: str) -> GraphNode | None:
        """Retrieve a node by its ``id`` property.

        Args:
            node_id: The node's ``id`` property value.

        Returns:
            The :class:`~lexigram.contracts.data.graph.GraphNode` or ``None``.

        """
        cypher = "MATCH (n {id: $id}) RETURN n"

        async def _work(tx: AsyncManagedTransaction) -> Any:
            result = await tx.run(cypher, id=node_id)
            record = await result.single()
            return record["n"] if record else None

        async with self._driver.session(database=self._database) as session:
            rn = await session.execute_read(_work)
            if not rn:
                return None
            return GraphNode(id=rn["id"], labels=tuple(rn.labels), properties=dict(rn))

    async def find_nodes(
        self,
        labels: list[str] | None = None,
        filter: PropertyFilter | None = None,  # noqa: A002
        limit: int = 100,
        skip: int = 0,
    ) -> list[GraphNode]:
        """Find nodes with optional label filtering.

        Args:
            labels: Optional label filter; all labels must match.
            filter: Unused.
            limit: Maximum results.
            skip: Results to skip.

        Returns:
            Matching :class:`~lexigram.contracts.data.graph.GraphNode` instances.

        """
        label_str = ":" + ":".join(labels) if labels else ""
        cypher = f"MATCH (n{label_str}) RETURN n SKIP {skip} LIMIT {limit}"

        async def _work(tx: AsyncManagedTransaction) -> list[dict[str, Any]]:
            result = await tx.run(cypher)
            return [{"n": record["n"]} async for record in result]

        async with self._driver.session(database=self._database) as session:
            records = await session.execute_read(_work)
            nodes = []
            for record in records:
                rn = record["n"]
                nodes.append(
                    GraphNode(
                        id=rn["id"], labels=tuple(rn.labels), properties=dict(rn)
                    ),
                )
            return nodes

    async def create_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: str,
        properties: dict[str, Any] | None = None,
    ) -> EdgeResult:
        """Create a directed relationship between two nodes.

        Args:
            source_id: Source node ``id`` property.
            target_id: Target node ``id`` property.
            edge_type: Relationship type.
            properties: Optional relationship properties.

        Returns:
            :class:`~lexigram.contracts.data.graph.EdgeResult` with the
            element ID of the new relationship.

        """
        cypher = f"""
            MATCH (s {{id: $source_id}}), (t {{id: $target_id}})
            CREATE (s)-[r:{edge_type} $props]->(t)
            RETURN elementId(r) as id
        """

        async def _work(tx: AsyncManagedTransaction) -> Any:
            result = await tx.run(
                cypher,
                source_id=source_id,
                target_id=target_id,
                props=properties or {},
            )
            record = await result.single()
            return record["id"] if record else None

        async with self._driver.session(database=self._database) as session:
            eid = await session.execute_write(_work)
            return EdgeResult(id=eid)

    async def traverse(self, query: TraversalQuery) -> list[GraphPath]:
        """Execute a traversal query via compiled Cypher.

        Args:
            query: Traversal parameters including start node, depth, and
                relationship type filters.

        Returns:
            All :class:`~lexigram.contracts.data.graph.GraphPath` instances
            found by the traversal.

        """
        from lexigram.graph.backends.neo4j.cypher import (
            CypherCompiler,  # noqa: PLC0415 — circular import avoidance; cypher module imports from this module's sibling
        )

        compiler = CypherCompiler()
        cypher, params = compiler.compile_traversal(query)

        async def _work(tx: AsyncManagedTransaction) -> list[dict[str, Any]]:
            result = await tx.run(cypher, params)
            return [dict(record) async for record in result]

        async with self._driver.session(database=self._database) as session:
            records = await session.execute_read(_work)
            paths = []
            for record in records:
                if "path" in record:
                    p = record["path"]
                    nodes = [
                        GraphNode(
                            id=n["id"],
                            labels=tuple(n.labels),
                            properties=dict(n),
                        )
                        for n in p.nodes
                    ]
                    edges = [
                        GraphEdge(
                            id=str(r.element_id),
                            type=r.type,
                            source_id=str(r.start_node.element_id),
                            target_id=str(r.end_node.element_id),
                            properties=dict(r),
                        )
                        for r in p.relationships
                    ]
                    paths.append(GraphPath(nodes=tuple(nodes), edges=tuple(edges)))
            return paths

    async def query(
        self,
        query_string: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a raw Cypher query string.

        Args:
            query_string: Cypher query.
            parameters: Optional parameter bindings.

        Returns:
            List of record dicts.

        """
        async with self._driver.session(database=self._database) as session:
            result = await session.run(query_string, parameters or {})
            return [dict(record) for record in await result.data()]
