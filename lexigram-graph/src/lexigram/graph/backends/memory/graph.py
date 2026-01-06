"""In-memory graph implementation."""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Any
import uuid

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
    from lexigram.contracts.data.graph.filters import PropertyFilter


class InMemoryGraph(BaseGraph):
    """In-memory graph implementation."""

    def __init__(self, name: str | None = None) -> None:
        super().__init__(name)
        self._nodes: dict[str, GraphNode] = {}
        self._edges: dict[str, GraphEdge] = {}

    async def create_node(
        self,
        labels: list[str],
        properties: dict[str, Any] | None = None,
        node_id: str | None = None,
    ) -> NodeResult:
        """Create a node and store it in memory.

        Args:
            labels: Node labels.
            properties: Optional property map.
            node_id: Optional explicit node ID; generated if omitted.

        Returns:
            :class:`~lexigram.contracts.data.graph.NodeResult` with the
            assigned node ID.

        """
        nid = node_id or str(uuid.uuid4())
        node = GraphNode(id=nid, labels=tuple(labels), properties=properties or {})
        self._nodes[nid] = node
        return NodeResult(id=nid)

    async def get_node(self, node_id: str) -> GraphNode | None:
        """Retrieve a node by ID.

        Args:
            node_id: The node ID to look up.

        Returns:
            The :class:`~lexigram.contracts.data.graph.GraphNode` or ``None``.

        """
        return self._nodes.get(node_id)

    async def find_nodes(
        self,
        labels: list[str] | None = None,
        filter: PropertyFilter | None = None,  # noqa: A002
        limit: int = 100,
        skip: int = 0,
    ) -> list[GraphNode]:
        """Find nodes with optional label filtering.

        Args:
            labels: Optional list of labels; all must match.
            filter: Unused by the in-memory backend.
            limit: Maximum number of results.
            skip: Number of results to skip.

        Returns:
            Matching :class:`~lexigram.contracts.data.graph.GraphNode` instances.

        """
        results = list(self._nodes.values())
        if labels:
            results = [n for n in results if all(label in n.labels for label in labels)]
        return results[skip : skip + limit]

    async def create_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: str,
        properties: dict[str, Any] | None = None,
    ) -> EdgeResult:
        """Create a directed edge between two nodes.

        Args:
            source_id: Source node ID.
            target_id: Target node ID.
            edge_type: Relationship type label.
            properties: Optional property map.

        Returns:
            :class:`~lexigram.contracts.data.graph.EdgeResult` with the
            assigned edge ID.

        """
        eid = str(uuid.uuid4())
        edge = GraphEdge(
            id=eid,
            type=edge_type,
            source_id=source_id,
            target_id=target_id,
            properties=properties or {},
        )
        self._edges[eid] = edge
        return EdgeResult(id=eid)

    async def traverse(self, query: TraversalQuery) -> list[GraphPath]:
        """Perform a BFS traversal from the start node.

        Args:
            query: The traversal query describing start node, depth, and
                relationship type filters.

        Returns:
            All :class:`~lexigram.contracts.data.graph.GraphPath` instances
            discovered within *query.max_depth* hops.

        """
        if not query.start.node_ids:
            return []

        start_node = self._nodes.get(query.start.node_ids[0])
        if not start_node:
            return []

        step = query.steps[0] if query.steps else None
        max_depth = step.max_depth if step else 10
        edge_types = step.edge_types if step else None

        paths = []

        # Simple BFS
        queue = deque([GraphPath(nodes=(start_node,), edges=())])

        while queue:
            current_path = queue.popleft()
            if len(current_path.edges) >= max_depth:
                continue

            last_node = current_path.nodes[-1]

            # Find outgoing edges
            out_edges = [
                e
                for e in self._edges.values()
                if e.source_id == last_node.id
                and (not edge_types or e.type in edge_types)
            ]

            for edge in out_edges:
                target_node = self._nodes.get(edge.target_id)
                if target_node:
                    new_path = GraphPath(
                        nodes=(*current_path.nodes, target_node),
                        edges=(*current_path.edges, edge),
                    )
                    paths.append(new_path)
                    queue.append(new_path)

        return paths

    async def query(
        self,
        query_string: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Not supported by the in-memory backend.

        Args:
            query_string: Ignored.
            parameters: Ignored.

        Raises:
            NotImplementedError: Always; the in-memory backend does not
                support Cypher queries.

        """
        msg = "In-memory does not support Cypher"
        raise NotImplementedError(msg)
