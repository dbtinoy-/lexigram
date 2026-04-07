"""In-memory graph store backend."""

from __future__ import annotations

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.data.graph import (
    GraphInfo,
)
from lexigram.graph.backends.base import BaseGraphStore
from lexigram.graph.backends.memory.graph import InMemoryGraph


class InMemoryGraphStore(BaseGraphStore):
    """In-memory graph store implementation."""

    def __init__(self) -> None:
        self._graphs: dict[str, InMemoryGraph] = {}

    async def connect(self) -> None:
        """No-op: in-memory store requires no connection."""

    async def disconnect(self) -> None:
        """Clear all in-memory graphs."""
        self._graphs.clear()

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:  # noqa: ASYNC109 — implements HealthCheckProtocol signature
        """Return a healthy status; no external dependency to check.

        Args:
            timeout: Unused for the in-memory backend.

        Returns:
            Always returns :attr:`~lexigram.contracts.core.health.HealthStatus.HEALTHY`.

        """
        return HealthCheckResult(component="graph.memory", status=HealthStatus.HEALTHY)

    async def get_graph(self, name: str | None = None) -> InMemoryGraph:
        """Get or create an in-memory graph by name.

        Args:
            name: Graph name. Defaults to ``"default"``.

        Returns:
            The :class:`InMemoryGraph` instance for the given name.

        """
        name = name or "default"
        if name not in self._graphs:
            self._graphs[name] = InMemoryGraph(name)
        return self._graphs[name]

    async def list_graphs(self) -> list[GraphInfo]:
        """List all graphs currently held in memory.

        Returns:
            A list of :class:`~lexigram.contracts.data.graph.GraphInfo` instances.

        """
        return [GraphInfo(name=name) for name in self._graphs]
