from __future__ import annotations

from dataclasses import dataclass

from lexigram.contracts.domain.events import DomainEvent


@dataclass(frozen=True, init=False)
class GraphConnectedEvent(DomainEvent):
    """Raised when a graph database connection is established.

    Downstream: observability, health monitoring.
    """

    backend: str


@dataclass(frozen=True, init=False)
class GraphDisconnectedEvent(DomainEvent):
    """Raised when a graph database connection is closed.

    Downstream: observability, cleanup hooks.
    """

    backend: str


@dataclass(frozen=True, init=False)
class GraphNodeCreatedEvent(DomainEvent):
    """Raised when a node is created in the graph.

    Downstream: audit logging, event sourcing.
    """

    node_id: str
    labels: tuple[str, ...]


@dataclass(frozen=True, init=False)
class GraphEdgeCreatedEvent(DomainEvent):
    """Raised when an edge (relationship) is created between two nodes.

    Downstream: audit logging, event sourcing.
    """

    source_id: str
    target_id: str
    relationship_type: str


@dataclass(frozen=True, init=False)
class GraphQueryExecutedEvent(DomainEvent):
    """Raised when a graph query is executed (e.g., Cypher).

    Downstream: analytics, slow query logging.
    """

    query_type: str
    result_count: int
