"""Graph store registry — registry-based dispatch of graph backends."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from lexigram.graph.constants import BACKEND_MEMORY, BACKEND_NEO4J

GraphStoreBuilder = Callable[[Any], Any]


class GraphStoreRegistry:
    """Registry of graph-store builders, keyed by backend name.

    A backend name maps to a builder that constructs the corresponding
    graph store from a :class:`~lexigram.graph.config.GraphConfig`.

    Usage::

        registry = GraphStoreRegistry.with_defaults()
        store = registry.create_store("memory", config)
    """

    def __init__(self) -> None:
        """Initialise an empty backend registry."""
        self._builders: dict[str, GraphStoreBuilder] = {}

    @classmethod
    def with_defaults(cls) -> GraphStoreRegistry:
        """Return a registry populated with the built-in graph backends.

        Returns:
            A :class:`GraphStoreRegistry` pre-registered for neo4j and
            memory.
        """
        registry = cls()

        def _neo4j(config: Any) -> Any:
            from lexigram.graph.backends.neo4j import Neo4jGraphStore

            return Neo4jGraphStore(config=config.neo4j)

        def _memory(_config: Any) -> Any:
            from lexigram.graph.backends.memory import InMemoryGraphStore

            return InMemoryGraphStore()

        registry.register(BACKEND_NEO4J, _neo4j)
        registry.register(BACKEND_MEMORY, _memory)
        return registry

    def register(self, backend: str, builder: GraphStoreBuilder) -> None:
        """Register a builder under a backend name.

        Args:
            backend: Backend name (e.g. ``"neo4j"``).
            builder: Callable ``(GraphConfig) -> GraphStoreProtocol``.
        """
        self._builders[backend] = builder

    def create_store(self, backend: str, config: Any) -> Any:
        """Build a graph store for a backend name.

        Args:
            backend: Backend name to dispatch on.
            config: GraphConfig used to construct the backend.

        Returns:
            An instantiated graph store.

        Raises:
            ValueError: If *backend* is not a registered backend.
        """
        builder = self._builders.get(backend)
        if builder is None:
            msg = f"Unknown graph backend: {backend}"
            raise ValueError(msg)
        return builder(config)

    def backends(self) -> list[str]:
        """Return the registered backend names.

        Returns:
            List of backend names in registration order.
        """
        return list(self._builders.keys())

    def __contains__(self, backend: str) -> bool:
        return backend in self._builders


__all__ = ["GraphStoreBuilder", "GraphStoreRegistry"]
