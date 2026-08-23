"""DI provider for the graph sub-namespace of lexigram-nosql."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from lexigram.contracts.core import HealthCheckResult, HealthStatus, ProviderPriority
from lexigram.contracts.data.graph.protocols import GraphStoreProtocol
from lexigram.di.provider import Provider
from lexigram.graph.config import GraphConfig
from lexigram.graph.constants import BACKEND_MEMORY, BACKEND_NEO4J
from lexigram.logging.factory import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )
    from lexigram.graph.backends.memory.backend import InMemoryGraphStore
    from lexigram.graph.backends.neo4j.backend import Neo4jGraphStore

logger = get_logger(__name__)


class GraphProvider(Provider):
    """Register graph store services into the DI container."""

    name = "graph"
    priority = ProviderPriority.INFRASTRUCTURE
    config_key: str | None = "graph"
    config_model: type | None = GraphConfig

    def __init__(self, config: GraphConfig | None = None) -> None:
        super().__init__()
        self._requested_config = config
        self._config = config or GraphConfig()
        self._store: GraphStoreProtocol | None = None

    async def register(
        self,
        container: ContainerRegistrarProtocol,
    ) -> None:
        """Register graph store bindings into the container.

        Args:
            container: The DI registrar to register services into.

        Raises:
            ValueError: If an unknown backend is specified in config.

        """
        self._config = self._requested_config or (
            self.config
            if isinstance(getattr(self, "config", None), GraphConfig)
            else self._config
        )
        container.singleton(GraphConfig, self._config)

        if not self._config.enabled:
            logger.info("graph_disabled", reason="GraphConfig.enabled=False")
            return

        backend = self._config.backend

        if backend == BACKEND_NEO4J:
            container.singleton(
                GraphStoreProtocol,
                factory=lambda: self._create_neo4j_store(self._config),
            )
        elif backend == BACKEND_MEMORY:
            container.singleton(
                GraphStoreProtocol,
                factory=self._create_memory_store,
            )
        else:
            msg = f"Unknown graph backend: {backend}"
            raise ValueError(msg)

        logger.info("graph_provider_registered", backend=backend)

    async def _maybe_wrap_with_tenancy(
        self,
        store: GraphStoreProtocol,
        container: ContainerResolverProtocol,
    ) -> GraphStoreProtocol:
        """Wrap *store* with tenant decorators when tenancy is enabled."""
        if not self._config.tenancy.enabled:
            return store

        from lexigram.contracts.data.graph.tenancy import GraphTenancyStrategy
        from lexigram.graph.tenancy.decorator import TenantGraphStoreDecorator
        from lexigram.graph.tenancy.resolver import TemplatedTenantCollectionResolver
        from lexigram.primitives.context import Context

        ctx = await container.resolve(Context)
        resolver: Any = TemplatedTenantCollectionResolver(
            template=self._config.tenancy.template,
        )
        return TenantGraphStoreDecorator(
            inner=store,
            resolver=resolver,
            ctx=ctx,
            strategy=GraphTenancyStrategy(self._config.tenancy.strategy),
        )

    async def boot(
        self,
        container: ContainerResolverProtocol,
    ) -> None:
        """Connect to the graph store after the container is fully built.

        Args:
            container: The DI resolver to obtain the graph store from.

        """
        if not self._config.enabled:
            return

        store = await container.resolve(GraphStoreProtocol)
        self._store = store
        await store.connect()
        self._store = await self._maybe_wrap_with_tenancy(self._store, container)
        container.bind(GraphStoreProtocol, self._store)  # type: ignore[type-abstract]
        logger.info("graph_store_connected", backend=self._config.backend)

    async def shutdown(self) -> None:
        """Disconnect from the graph store during application shutdown."""
        if self._store is not None:
            await self._store.disconnect()
            logger.info("graph_store_disconnected")
            self._store = None

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:  # noqa: ASYNC109 — implements HealthCheckProtocol signature
        """Check provider health.

        Args:
            timeout: Maximum seconds to wait for health check response.

        Returns:
            :class:`~lexigram.contracts.core.HealthCheckResult` with status
            and component details.

        """
        start = time.perf_counter()

        if not self._config.enabled:
            return HealthCheckResult(
                component="graph",
                status=HealthStatus.DEGRADED,
                message="graph not enabled",
                duration_ms=(time.perf_counter() - start) * 1000,
            )

        if self._store is None:
            return HealthCheckResult(
                component="graph",
                status=HealthStatus.DEGRADED,
                message="graph store not initialized",
                duration_ms=(time.perf_counter() - start) * 1000,
            )

        try:
            store_result = await self._store.health_check(timeout=timeout)
            return HealthCheckResult(
                component="graph",
                status=store_result.status,
                details=store_result.details,
                error=store_result.error,
                duration_ms=(time.perf_counter() - start) * 1000,
            )
        except (ConnectionError, TimeoutError, RuntimeError) as exc:
            return HealthCheckResult(
                component="graph",
                status=HealthStatus.UNHEALTHY,
                error=str(exc),
                duration_ms=(time.perf_counter() - start) * 1000,
            )

    @staticmethod
    def _create_neo4j_store(config: GraphConfig) -> Neo4jGraphStore:
        from lexigram.graph.backends.neo4j import (
            Neo4jGraphStore,  # noqa: PLC0415 — optional heavy dep; neo4j driver is only imported when neo4j backend is selected
        )

        return Neo4jGraphStore(config=config.neo4j)

    @staticmethod
    def _create_memory_store() -> InMemoryGraphStore:
        from lexigram.graph.backends.memory import (
            InMemoryGraphStore,  # noqa: PLC0415 — optional dep; deferred to avoid importing driver modules at module load time
        )

        return InMemoryGraphStore()
