"""Graph store exceptions."""

from __future__ import annotations

from lexigram.contracts.exceptions import InfrastructureError


class GraphError(InfrastructureError):
    """Base exception for all graph store operations."""

    _code: str = "LEX_ERR_GRAPH_001"


class GraphConnectionError(GraphError):
    """Failed to connect to the graph store."""

    _code: str = "LEX_ERR_GRAPH_002"


class GraphNotFoundError(GraphError):
    """Requested graph database does not exist."""

    _code: str = "LEX_ERR_GRAPH_003"

    def __init__(self, graph_name: str) -> None:
        self.graph_name = graph_name
        super().__init__(
            f"Graph database '{graph_name}' not found",
        )


class GraphAlreadyExistsError(GraphError):
    """Attempted to create a graph that already exists."""

    _code: str = "LEX_ERR_GRAPH_004"

    def __init__(self, graph_name: str) -> None:
        self.graph_name = graph_name
        super().__init__(
            f"Graph database '{graph_name}' already exists",
        )


class GraphNodeNotFoundError(GraphError):
    """Referenced node does not exist."""

    _code: str = "LEX_ERR_GRAPH_005"

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        super().__init__(
            f"Node '{node_id}' not found",
        )


class GraphEdgeNotFoundError(GraphError):
    """Referenced edge does not exist."""

    _code: str = "LEX_ERR_GRAPH_006"

    def __init__(self, edge_id: str) -> None:
        self.edge_id = edge_id
        super().__init__(
            f"Edge '{edge_id}' not found",
        )


class DetachRequiredError(GraphError):
    """Node has edges and detach=False was specified."""

    _code: str = "LEX_ERR_GRAPH_007"

    def __init__(self, node_id: str, edge_count: int) -> None:
        self.node_id = node_id
        self.edge_count = edge_count
        super().__init__(
            f"Node '{node_id}' has {edge_count} edges. Use detach=True to delete them.",
        )


class TraversalError(GraphError):
    """Traversal query failed."""

    _code: str = "LEX_ERR_GRAPH_008"


class CypherCompilationError(GraphError):
    """Failed to compile a traversal query to Cypher."""

    _code: str = "LEX_ERR_GRAPH_009"

    def __init__(self, message: str) -> None:
        super().__init__(
            f"Cypher compilation failed: {message}",
        )


class GraphSchemaError(GraphError):
    """Schema operation (index, constraint) failed."""

    _code: str = "LEX_ERR_GRAPH_010"


class GraphTransactionError(GraphError):
    """Graph transaction failed."""

    _code: str = "LEX_ERR_GRAPH_011"


class GraphQueryError(GraphError):
    """Raw query execution failed."""

    _code: str = "LEX_ERR_GRAPH_012"


__all__ = [
    "CypherCompilationError",
    "DetachRequiredError",
    "GraphAlreadyExistsError",
    "GraphConnectionError",
    "GraphEdgeNotFoundError",
    "GraphError",
    "GraphNodeNotFoundError",
    "GraphNotFoundError",
    "GraphQueryError",
    "GraphSchemaError",
    "GraphTransactionError",
    "TraversalError",
]
