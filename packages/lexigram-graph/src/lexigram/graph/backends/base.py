"""Base abstract classes for graph store backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from lexigram.contracts.data.graph import (
    GraphProtocol,
    GraphStoreProtocol,
)

if TYPE_CHECKING:
    from lexigram.contracts.data.graph.enums import EdgeDirection
    from lexigram.contracts.data.graph.types import (
        BulkEdgeResult,
        BulkNodeResult,
        ConstraintSpec,
        EdgeSpec,
        GraphEdge,
        GraphNode,
        GraphPath,
        IndexSpec,
        NodeSpec,
    )


class BaseGraphStore(GraphStoreProtocol, ABC):
    """Common logic for all graph store implementations."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection."""

    async def create_graph(self, name: str) -> None:
        """Create a new graph database.

        Not all backends support creating graphs dynamically.

        Raises:
            NotImplementedError: Always; override in backend-specific subclass.

        """
        msg = f"create_graph not implemented by {type(self).__name__}"
        raise NotImplementedError(msg)

    async def delete_graph(self, name: str) -> None:
        """Delete a graph database and all its data.

        Not all backends support deleting graphs.

        Raises:
            NotImplementedError: Always; override in backend-specific subclass.

        """
        msg = f"delete_graph not implemented by {type(self).__name__}"
        raise NotImplementedError(msg)


class BaseGraph(GraphProtocol):
    """Common logic for all graph database implementations."""

    def __init__(self, name: str | None = None) -> None:
        self._name = name or "default"

    @property
    def name(self) -> str:
        """Graph name."""
        return self._name

    # ── Default stubs for optional Protocol methods ────────────────

    async def update_node(
        self,
        node_id: str,
        properties: dict[str, Any],
        merge: bool = True,
    ) -> bool:
        """Override in subclass."""
        msg = f"update_node not implemented by {type(self).__name__}"
        raise NotImplementedError(msg)

    async def delete_node(self, node_id: str, detach: bool = True) -> bool:
        """Override in subclass."""
        msg = f"delete_node not implemented by {type(self).__name__}"
        raise NotImplementedError(msg)

    async def neighbors(
        self,
        node_id: str,
        depth: int = 1,
        direction: EdgeDirection = ...,  # type: ignore[assignment]
        edge_types: list[str] | None = None,
    ) -> list[GraphNode]:
        """Override in subclass."""
        msg = f"neighbors not implemented by {type(self).__name__}"
        raise NotImplementedError(msg)

    async def count_nodes(self) -> int:
        """Override in subclass."""
        msg = f"count_nodes not implemented by {type(self).__name__}"
        raise NotImplementedError(msg)

    async def count_edges(self) -> int:
        """Override in subclass."""
        msg = f"count_edges not implemented by {type(self).__name__}"
        raise NotImplementedError(msg)

    async def get_labels(self) -> list[str]:
        """Override in subclass."""
        msg = f"get_labels not implemented by {type(self).__name__}"
        raise NotImplementedError(msg)

    async def get_edge_types(self) -> list[str]:
        """Override in subclass."""
        msg = f"get_edge_types not implemented by {type(self).__name__}"
        raise NotImplementedError(msg)

    async def get_edge(self, edge_id: str) -> GraphEdge | None:
        """Override in subclass."""
        msg = f"get_edge not implemented by {type(self).__name__}"
        raise NotImplementedError(msg)

    async def get_edges(
        self,
        node_id: str,
        direction: EdgeDirection = ...,  # type: ignore[assignment]
        edge_types: list[str] | None = None,
        limit: int = 100,
    ) -> list[GraphEdge]:
        """Override in subclass."""
        msg = f"get_edges not implemented by {type(self).__name__}"
        raise NotImplementedError(msg)

    async def update_edge(
        self,
        edge_id: str,
        properties: dict[str, Any],
        merge: bool = True,
    ) -> bool:
        """Override in subclass."""
        msg = f"update_edge not implemented by {type(self).__name__}"
        raise NotImplementedError(msg)

    async def delete_edge(self, edge_id: str) -> bool:
        """Override in subclass."""
        msg = f"delete_edge not implemented by {type(self).__name__}"
        raise NotImplementedError(msg)

    async def shortest_path(
        self,
        from_id: str,
        to_id: str,
        max_depth: int = 10,
        edge_types: list[str] | None = None,
        direction: EdgeDirection = ...,  # type: ignore[assignment]
    ) -> GraphPath | None:
        """Override in subclass."""
        msg = f"shortest_path not implemented by {type(self).__name__}"
        raise NotImplementedError(msg)

    async def bulk_create_nodes(self, nodes: list[NodeSpec]) -> BulkNodeResult:
        """Override in subclass."""
        msg = f"bulk_create_nodes not implemented by {type(self).__name__}"
        raise NotImplementedError(msg)

    async def bulk_create_edges(self, edges: list[EdgeSpec]) -> BulkEdgeResult:
        """Override in subclass."""
        msg = f"bulk_create_edges not implemented by {type(self).__name__}"
        raise NotImplementedError(msg)

    async def create_index(self, spec: IndexSpec) -> None:
        """Override in subclass."""
        msg = f"create_index not implemented by {type(self).__name__}"
        raise NotImplementedError(msg)

    async def drop_index(self, name: str) -> None:
        """Override in subclass."""
        msg = f"drop_index not implemented by {type(self).__name__}"
        raise NotImplementedError(msg)

    async def create_constraint(self, spec: ConstraintSpec) -> None:
        """Override in subclass."""
        msg = f"create_constraint not implemented by {type(self).__name__}"
        raise NotImplementedError(msg)

    async def drop_constraint(self, name: str) -> None:
        """Override in subclass."""
        msg = f"drop_constraint not implemented by {type(self).__name__}"
        raise NotImplementedError(msg)
