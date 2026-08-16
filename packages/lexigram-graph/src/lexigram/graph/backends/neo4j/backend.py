"""Neo4j managed graph store backend."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.data.graph import (
    GraphInfo,
)
from lexigram.graph.backends.base import BaseGraphStore
from lexigram.graph.backends.neo4j.graph import Neo4jGraph
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from neo4j import AsyncDriver  # type: ignore[import-not-found]

    from lexigram.graph.config import Neo4jConfig

logger = get_logger(__name__)


class Neo4jGraphStore(BaseGraphStore):
    """Neo4j managed graph store backend."""

    def __init__(self, config: Neo4jConfig) -> None:
        self._config = config
        self._driver: AsyncDriver | None = None

    async def connect(self) -> None:
        """Connect to Neo4j and create foundational constraints.

        Creates a uniqueness constraint for the ``id`` property on ``Node``
        labels as a best-effort operation.
        """
        from neo4j import (
            AsyncGraphDatabase,  # noqa: PLC0415 — optional heavy dep; neo4j is only imported when connect() is actually called
        )

        self._driver = AsyncGraphDatabase.driver(
            self._config.uri,
            auth=(self._config.username, self._config.password.get_secret_value()),
        )
        # Create foundational uniqueness constraints for node IDs.
        # Best-effort: older Neo4j versions or permission restrictions may
        # prevent this from running.
        try:
            async with self._driver.session() as session:
                await session.run(
                    "CREATE CONSTRAINT node_id_unique IF NOT EXISTS "
                    "FOR (n:Node) REQUIRE n.id IS UNIQUE",
                )
        except Exception as e:  # noqa: BLE001 — constraint setup is best-effort; older Neo4j or permission issues are non-fatal
            logger.debug("neo4j_constraint_setup_skipped", error=str(e))

    async def disconnect(self) -> None:
        """Close the Neo4j driver."""
        if self._driver:
            await self._driver.close()
            self._driver = None

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:  # noqa: ASYNC109 — implements HealthCheckProtocol signature
        """Verify connectivity to Neo4j.

        Args:
            timeout: Unused; Neo4j driver manages its own timeout.

        Returns:
            :class:`~lexigram.contracts.core.health.HealthCheckResult` with
            HEALTHY or UNHEALTHY status.

        """
        if not self._driver:
            return HealthCheckResult(
                component="graph.neo4j",
                status=HealthStatus.UNHEALTHY,
            )
        try:
            await self._driver.verify_connectivity()
            return HealthCheckResult(
                component="graph.neo4j",
                status=HealthStatus.HEALTHY,
            )
        except Exception as e:  # noqa: BLE001 — Neo4j driver boundary; converts all neo4j exceptions to a health status
            return HealthCheckResult(
                component="graph.neo4j",
                status=HealthStatus.UNHEALTHY,
                message=str(e),
            )

    async def get_graph(self, name: str | None = None) -> Neo4jGraph:
        """Return a handle to a named Neo4j database.

        Args:
            name: Database name. Defaults to the driver default.

        Returns:
            A :class:`Neo4jGraph` instance scoped to the given database.

        Raises:
            RuntimeError: If not yet connected.

        """
        if not self._driver:
            msg = "Not connected"
            raise RuntimeError(msg)
        return Neo4jGraph(self._driver, name)

    async def list_graphs(self) -> list[GraphInfo]:
        """List all databases visible to the connected Neo4j instance.

        Returns:
            A list of :class:`~lexigram.contracts.data.graph.GraphInfo`.

        """
        res = await self.query("SHOW DATABASES")
        return [GraphInfo(name=row["name"]) for row in res]

    async def query(self, query_string: str) -> list[dict[str, Any]]:
        """Execute a raw Cypher query and return all records.

        Args:
            query_string: Cypher query to execute.

        Returns:
            List of record dicts.

        Raises:
            RuntimeError: If not yet connected.

        """
        if not self._driver:
            msg = "Not connected"
            raise RuntimeError(msg)
        async with self._driver.session() as session:
            result = await session.run(query_string)
            return [dict(record) for record in await result.data()]
