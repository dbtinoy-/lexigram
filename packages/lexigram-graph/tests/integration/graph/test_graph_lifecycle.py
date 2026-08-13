"""Integration tests for the lexigram-graph provider lifecycle.

Tests the complete DI lifecycle for the graph subsystem using the real
Container and in-memory backend — no external services required.

Flow under test:
  GraphProvider.register() → GraphProvider.boot() → resolve → health_check()
  → GraphProvider.shutdown()
"""

from __future__ import annotations

import pytest

from lexigram.contracts.core.health import HealthStatus
from lexigram.contracts.data.graph.protocols import GraphStoreProtocol
from lexigram.di.container import Container
from lexigram.graph.config import GraphConfig
from lexigram.graph.di.provider import GraphProvider

pytestmark = [pytest.mark.integration]


class TestGraphProviderLifecycle:
    """Full provider lifecycle for the memory-backed graph store.

    Exercises the register → boot → resolve → health_check → shutdown
    sequence using the real DI Container and InMemoryGraphStore.
    """

    @pytest.fixture
    async def provider(self) -> GraphProvider:
        """Build a GraphProvider configured for the in-memory backend."""
        return GraphProvider(config=GraphConfig(backend="memory"))

    @pytest.fixture
    async def booted_container(self, provider: GraphProvider):
        """Container with GraphProvider fully registered and booted."""
        container = Container()
        await provider.register(container)
        await provider.boot(container)
        yield container
        await provider.shutdown()

    # ------------------------------------------------------------------
    # register phase
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_register_binds_graph_config_singleton(
        self, provider: GraphProvider
    ) -> None:
        """GraphConfig is available from the container after register()."""
        container = Container()
        await provider.register(container)

        config = await container.resolve(GraphConfig)

        assert isinstance(config, GraphConfig)
        assert config.backend == "memory"

        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_register_binds_graph_store_protocol(
        self, provider: GraphProvider
    ) -> None:
        """GraphStoreProtocol binding is registered before boot."""
        container = Container()
        await provider.register(container)

        # Resolution should succeed (lazy factory is evaluated here)
        store = await container.resolve(GraphStoreProtocol)

        assert store is not None

        await provider.shutdown()

    # ------------------------------------------------------------------
    # boot phase
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_boot_resolves_store_and_connects(
        self, booted_container: Container
    ) -> None:
        """After boot, GraphStoreProtocol is resolvable and connected."""
        store = await booted_container.resolve(GraphStoreProtocol)

        assert store is not None

    @pytest.mark.asyncio
    async def test_boot_singleton_is_same_instance(
        self, booted_container: Container
    ) -> None:
        """Resolving GraphStoreProtocol twice returns the same singleton."""
        store_a = await booted_container.resolve(GraphStoreProtocol)
        store_b = await booted_container.resolve(GraphStoreProtocol)

        assert store_a is store_b

    # ------------------------------------------------------------------
    # health check
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy(
        self, booted_container: Container
    ) -> None:
        """InMemoryGraphStore.health_check() reports HEALTHY after boot."""
        store = await booted_container.resolve(GraphStoreProtocol)
        result = await store.health_check()

        assert result.status == HealthStatus.HEALTHY

    # ------------------------------------------------------------------
    # shutdown phase
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_shutdown_is_idempotent(self) -> None:
        """Calling shutdown() twice must not raise."""
        provider = GraphProvider(config=GraphConfig(backend="memory"))
        container = Container()
        await provider.register(container)
        await provider.boot(container)

        await provider.shutdown()
        await provider.shutdown()  # second call must be safe

    # ------------------------------------------------------------------
    # disabled backend
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_disabled_graph_provider_does_not_register_store(self) -> None:
        """When GraphConfig.enabled=False, no GraphStoreProtocol is bound."""
        provider = GraphProvider(config=GraphConfig(enabled=False))
        container = Container()
        await provider.register(container)

        store = await container.resolve_optional(GraphStoreProtocol)

        assert store is None

        await provider.shutdown()
