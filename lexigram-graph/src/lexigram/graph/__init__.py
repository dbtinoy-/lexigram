"""Lexigram Graph — Graph database backends for the Lexigram Framework.

Provides pluggable graph storage and traversal with Neo4j support.
Application code depends on ``GraphStoreProtocol`` from
``lexigram-contracts``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.graph.constants import __version__ as __version__

if TYPE_CHECKING:
    from lexigram.contracts.data.graph.protocols import (
        GraphProtocol,
        GraphStoreProtocol,
    )
    from lexigram.graph.backends.base import BaseGraph, BaseGraphStore
    from lexigram.graph.backends.neo4j import Neo4jGraph, Neo4jGraphStore
    from lexigram.graph.config import GraphConfig, GraphTenancyConfig, Neo4jConfig
    from lexigram.graph.di.provider import GraphProvider
    from lexigram.graph.events import (
        GraphConnectedEvent,
        GraphDisconnectedEvent,
        GraphEdgeCreatedEvent,
        GraphNodeCreatedEvent,
        GraphQueryExecutedEvent,
    )
    from lexigram.graph.module import GraphModule

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # --- Base ---
    "BaseGraphStore": ("lexigram.graph.backends.base", "BaseGraphStore"),
    "BaseGraph": ("lexigram.graph.backends.base", "BaseGraph"),
    # --- Drivers ---
    "Neo4jGraphStore": ("lexigram.graph.backends.neo4j", "Neo4jGraphStore"),
    "Neo4jGraph": ("lexigram.graph.backends.neo4j", "Neo4jGraph"),
    # --- Events ---
    "GraphConnectedEvent": ("lexigram.graph.events", "GraphConnectedEvent"),
    "GraphDisconnectedEvent": ("lexigram.graph.events", "GraphDisconnectedEvent"),
    "GraphNodeCreatedEvent": ("lexigram.graph.events", "GraphNodeCreatedEvent"),
    "GraphEdgeCreatedEvent": ("lexigram.graph.events", "GraphEdgeCreatedEvent"),
    "GraphQueryExecutedEvent": ("lexigram.graph.events", "GraphQueryExecutedEvent"),
    # --- Framework ---
    "GraphConfig": ("lexigram.graph.config", "GraphConfig"),
    "GraphTenancyConfig": ("lexigram.graph.config", "GraphTenancyConfig"),
    "Neo4jConfig": ("lexigram.graph.config", "Neo4jConfig"),
    "GraphProvider": ("lexigram.graph.di.provider", "GraphProvider"),
    "GraphModule": ("lexigram.graph.module", "GraphModule"),
    # --- Protocols ---
    "GraphProtocol": ("lexigram.graph.protocols", "GraphProtocol"),
    "GraphStoreProtocol": ("lexigram.graph.protocols", "GraphStoreProtocol"),
    # --- Tenancy ---
    "TenantGraphStoreDecorator": (
        "lexigram.graph.tenancy.decorator",
        "TenantGraphStoreDecorator",
    ),
    "TenantPropertyFilterGraph": (
        "lexigram.graph.tenancy.decorator",
        "TenantPropertyFilterGraph",
    ),
}


def __getattr__(name: str) -> Any:
    """Lazy-load symbols on first access."""
    if name in _LAZY_IMPORTS:
        import importlib  # noqa: PLC0415 — lazy-load pattern; heavy driver modules are deferred until first attribute access

        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


def __dir__() -> list[str]:
    """Enumerate available attributes for IDE support."""
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = [
    "BaseGraph",
    "BaseGraphStore",
    "GraphConfig",
    "GraphConnectedEvent",
    "GraphDisconnectedEvent",
    "GraphEdgeCreatedEvent",
    "GraphModule",
    "GraphNodeCreatedEvent",
    "GraphProtocol",
    "GraphProvider",
    "GraphQueryExecutedEvent",
    "GraphStoreProtocol",
    "GraphTenancyConfig",
    "Neo4jConfig",
    "Neo4jGraph",
    "Neo4jGraphStore",
    "TenantGraphStoreDecorator",
    "TenantPropertyFilterGraph",
]
