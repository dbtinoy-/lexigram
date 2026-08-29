from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.graph.config import GraphConfig
from lexigram.graph.di.provider import GraphProvider


class _StoreStub:
    def __init__(self, healthy: bool = True) -> None:
        self._healthy = healthy
        self.connect = AsyncMock()
        self.disconnect = AsyncMock()
        self.health_check = AsyncMock(
            return_value=HealthCheckResult(
                component="graph-store",
                status=HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY,
            )
        )


class TestGraphProviderInitialization:
    def test_provider_initializes_with_default_config(self) -> None:
        provider = GraphProvider()
        assert provider.name == "graph"
        assert provider._effective_config is not None

    def test_provider_initializes_with_custom_config(self) -> None:
        config = GraphConfig(enabled=True, backend="neo4j")
        provider = GraphProvider(config=config)
        assert provider._effective_config is config

    def test_provider_has_correct_priority(self) -> None:
        from lexigram.contracts.core import ProviderPriority

        provider = GraphProvider()
        assert provider.priority == ProviderPriority.INFRASTRUCTURE


class TestGraphProviderRegister:
    @pytest.mark.asyncio
    async def test_register_singleton_config(self) -> None:
        class RegistrarStub:
            def __init__(self) -> None:
                self.calls: list[tuple[object, object]] = []

            def singleton(self, service_type: object, instance: object = None, **kwargs: object) -> None:
                self.calls.append((service_type, instance))

        provider = GraphProvider(config=GraphConfig(enabled=False))
        container = RegistrarStub()

        await provider.register(container)

        assert any(call[0] is GraphConfig for call in container.calls)

    @pytest.mark.asyncio
    async def test_register_returns_early_when_disabled(self) -> None:
        class RegistrarStub:
            def __init__(self) -> None:
                self.calls: list[tuple[object, object]] = []

            def singleton(self, service_type: object, instance: object = None, **kwargs: object) -> None:
                self.calls.append((service_type, instance))

        provider = GraphProvider(config=GraphConfig(enabled=False))
        container = RegistrarStub()

        await provider.register(container)

        store_calls = [call for call in container.calls if call[0].__name__ == "GraphStoreProtocol"]
        assert len(store_calls) == 0

    @pytest.mark.asyncio
    async def test_register_memory_backend(self) -> None:
        class RegistrarStub:
            def __init__(self) -> None:
                self.calls: list[tuple[object, object, dict[str, object]]] = []

            def singleton(self, service_type: object, instance: object = None, factory: object = None, **kwargs: object) -> None:
                self.calls.append((service_type, instance, {"factory": factory}))

        provider = GraphProvider(config=GraphConfig(backend="memory"))
        container = RegistrarStub()

        await provider.register(container)

        assert any(
            call[0].__name__ == "GraphStoreProtocol"
            and call[2].get("factory") is not None
            for call in container.calls
        )

    @pytest.mark.asyncio
    async def test_register_neo4j_backend(self) -> None:
        class RegistrarStub:
            def __init__(self) -> None:
                self.calls: list[tuple[object, object, dict[str, object]]] = []

            def singleton(self, service_type: object, instance: object = None, factory: object = None, **kwargs: object) -> None:
                self.calls.append((service_type, instance, {"factory": factory}))

        config = GraphConfig(backend="neo4j")
        provider = GraphProvider(config=config)
        container = RegistrarStub()

        await provider.register(container)

        assert any(
            call[0].__name__ == "GraphStoreProtocol"
            and call[2].get("factory") is not None
            for call in container.calls
        )

    def test_register_unknown_backend_config_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported backend"):
            GraphConfig(backend="unknown")


class TestGraphProviderBoot:
    @pytest.mark.asyncio
    async def test_boot_returns_early_when_disabled(self) -> None:
        provider = GraphProvider(config=GraphConfig(enabled=False))

        await provider.boot(object())

        assert provider._store is None

    @pytest.mark.asyncio
    async def test_boot_resolves_store_and_connects(self) -> None:
        store = _StoreStub()
        store.connect = AsyncMock()

        class ResolverStub:
            async def resolve(self, service_type: object) -> object:
                return store

            def bind(self, service_type: type, instance: object) -> None:
                pass

        provider = GraphProvider(config=GraphConfig(backend="memory"))
        container = ResolverStub()

        await provider.boot(container)

        store.connect.assert_awaited_once()
        assert provider._store is store


class TestGraphProviderShutdown:
    @pytest.mark.asyncio
    async def test_shutdown_disconnects_store(self) -> None:
        store = _StoreStub()
        store.disconnect = AsyncMock()

        provider = GraphProvider()
        provider._store = store

        await provider.shutdown()

        store.disconnect.assert_awaited_once()
        assert provider._store is None

    @pytest.mark.asyncio
    async def test_shutdown_handles_none_store(self) -> None:
        provider = GraphProvider()
        provider._store = None

        await provider.shutdown()

        assert provider._store is None


class TestGraphProviderHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_when_disabled(self) -> None:
        provider = GraphProvider(config=GraphConfig(enabled=False))

        result = await provider.health_check()

        assert result.status == HealthStatus.DEGRADED
        assert "not enabled" in result.message.lower()

    @pytest.mark.asyncio
    async def test_health_check_when_store_not_initialized(self) -> None:
        provider = GraphProvider(config=GraphConfig(enabled=True))

        result = await provider.health_check()

        assert result.status == HealthStatus.DEGRADED
        assert "not initialized" in result.message.lower()

    @pytest.mark.asyncio
    async def test_health_check_returns_store_result(self) -> None:
        store = _StoreStub(healthy=True)
        provider = GraphProvider(config=GraphConfig(enabled=True))
        provider._store = store

        result = await provider.health_check()

        assert result.status == HealthStatus.HEALTHY
        assert result.component == "graph"

    @pytest.mark.asyncio
    async def test_health_check_forwards_unhealthy_store(self) -> None:
        store = _StoreStub(healthy=False)
        provider = GraphProvider(config=GraphConfig(enabled=True))
        provider._store = store

        result = await provider.health_check()

        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_health_check_catches_connection_error(self) -> None:
        store = AsyncMock()
        store.health_check = AsyncMock(side_effect=ConnectionError("connection failed"))
        provider = GraphProvider(config=GraphConfig(enabled=True))
        provider._store = store

        result = await provider.health_check()

        assert result.status == HealthStatus.UNHEALTHY
        assert "connection failed" in result.error.lower()

    @pytest.mark.asyncio
    async def test_health_check_catches_timeout_error(self) -> None:
        store = AsyncMock()
        store.health_check = AsyncMock(side_effect=TimeoutError("timeout"))
        provider = GraphProvider(config=GraphConfig(enabled=True))
        provider._store = store

        result = await provider.health_check()

        assert result.status == HealthStatus.UNHEALTHY
        assert "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_health_check_catches_runtime_error(self) -> None:
        store = AsyncMock()
        store.health_check = AsyncMock(side_effect=RuntimeError("runtime error"))
        provider = GraphProvider(config=GraphConfig(enabled=True))
        provider._store = store

        result = await provider.health_check()

        assert result.status == HealthStatus.UNHEALTHY
        assert "runtime error" in result.error.lower()

    @pytest.mark.asyncio
    async def test_health_check_includes_duration(self) -> None:
        store = _StoreStub(healthy=True)
        provider = GraphProvider(config=GraphConfig(enabled=True))
        provider._store = store

        result = await provider.health_check()

        assert result.duration_ms is not None
        assert result.duration_ms >= 0


class TestGraphProviderFactoryMethods:
    @pytest.mark.asyncio
    async def test_create_neo4j_store(self) -> None:
        from lexigram.graph.backends.neo4j import Neo4jGraphStore
        from lexigram.graph.backends.registry import GraphStoreRegistry
        from lexigram.graph.config import Neo4jConfig

        config = GraphConfig(backend="neo4j", neo4j=Neo4jConfig(uri="bolt://test:7687"))
        registry = GraphStoreRegistry.with_defaults()

        store = registry.create_store("neo4j", config)

        assert isinstance(store, Neo4jGraphStore)

    @pytest.mark.asyncio
    async def test_create_memory_store(self) -> None:
        from lexigram.graph.backends.memory import InMemoryGraphStore
        from lexigram.graph.backends.registry import GraphStoreRegistry

        registry = GraphStoreRegistry.with_defaults()
        store = registry.create_store("memory", GraphConfig())

        assert isinstance(store, InMemoryGraphStore)