"""Tests for NoSQLProvider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.nosql.config import NoSQLConfig
from lexigram.nosql.di.provider import NoSQLProvider


class TestNoSQLProvider:
    """Unit tests for NoSQLProvider single-backend functionality."""

    def test_initialization_default_config(self) -> None:
        """Zero-config construction defers config resolution to register()
        so the orchestrator can inject the yaml section first."""
        provider = NoSQLProvider()
        assert provider._config is None
        assert provider._store is None

    def test_initialization_custom_config(self) -> None:
        """Provider accepts custom NoSQLConfig."""
        config = NoSQLConfig(driver="mongodb", enabled=True)
        provider = NoSQLProvider(config=config)
        assert provider._config is config

    def test_from_config_factory(self) -> None:
        """from_config factory creates provider with given config."""
        config = NoSQLConfig(driver="mongodb", enabled=True)
        provider = NoSQLProvider.from_config(config)
        assert provider._config is config

    @pytest.mark.asyncio
    async def test_register_disabled_no_sql_registered(self) -> None:
        """When enabled=False, no store is registered (only config)."""
        config = NoSQLConfig(enabled=False)
        provider = NoSQLProvider(config=config)
        container = MagicMock()
        container.singleton = MagicMock()

        await provider.register(container)

        # Only NoSQLConfig is registered, no store
        assert container.singleton.call_count == 1

    @pytest.mark.asyncio
    async def test_register_single_backend_mongodb(self) -> None:
        """Single MongoDB backend is registered correctly."""
        config = NoSQLConfig(driver="mongodb", enabled=True)
        provider = NoSQLProvider(config=config)
        container = MagicMock()
        container.singleton = MagicMock()

        mock_store = MagicMock()
        with patch(
            "lexigram.nosql.di.provider.MongoDBDocumentStore", return_value=mock_store
        ):
            await provider.register(container)

        # NoSQLConfig + DocumentStoreProtocol + MongoDBDocumentStore
        assert container.singleton.call_count >= 2

    @pytest.mark.asyncio
    async def test_register_unsupported_driver_raises(self) -> None:
        """Unsupported driver raises ValueError."""
        config = NoSQLConfig(driver="unknown", enabled=True)
        provider = NoSQLProvider(config=config)
        container = MagicMock()

        with pytest.raises(ValueError, match="Unsupported NoSQL driver"):
            await provider.register(container)

    @pytest.mark.asyncio
    async def test_boot_connects_store(self) -> None:
        """boot() calls connect() on the store."""
        config = NoSQLConfig(driver="mongodb", enabled=True)
        provider = NoSQLProvider(config=config)
        container = MagicMock()
        container.singleton = MagicMock()

        mock_store = AsyncMock()
        mock_store.connect = AsyncMock()
        with patch(
            "lexigram.nosql.di.provider.MongoDBDocumentStore", return_value=mock_store
        ):
            await provider.register(container)
            await provider.boot(container)

        mock_store.connect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_shutdown_disconnects_store(self) -> None:
        """shutdown() calls disconnect() on the store."""
        config = NoSQLConfig(driver="mongodb", enabled=True)
        provider = NoSQLProvider(config=config)
        container = MagicMock()
        container.singleton = MagicMock()

        mock_store = AsyncMock()
        mock_store.disconnect = AsyncMock()
        with patch(
            "lexigram.nosql.di.provider.MongoDBDocumentStore", return_value=mock_store
        ):
            await provider.register(container)
            await provider.boot(container)
            await provider.shutdown()

        mock_store.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_health_check_disabled_returns_degraded(self) -> None:
        """health_check() returns DEGRADED when nosql is disabled."""
        config = NoSQLConfig(enabled=False)
        provider = NoSQLProvider(config=config)

        result = await provider.health_check(timeout=1.0)

        assert result.status == HealthStatus.DEGRADED
        assert "nosql not enabled" in result.message

    @pytest.mark.asyncio
    async def test_health_check_no_store_returns_degraded(self) -> None:
        """health_check() returns DEGRADED when store not initialized."""
        config = NoSQLConfig(driver="mongodb", enabled=True)
        provider = NoSQLProvider(config=config)
        provider._store = None

        result = await provider.health_check(timeout=1.0)

        assert result.status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_health_check_store_healthy(self) -> None:
        """health_check() returns healthy when store is healthy."""
        config = NoSQLConfig(driver="mongodb", enabled=True)
        provider = NoSQLProvider(config=config)

        mock_store = AsyncMock()
        mock_store.health_check = AsyncMock(
            return_value=HealthCheckResult(
                component="mongodb",
                status=HealthStatus.HEALTHY,
            )
        )
        provider._store = mock_store

        result = await provider.health_check(timeout=1.0)

        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_health_check_store_unhealthy(self) -> None:
        """health_check() returns UNHEALTHY when store health_check raises."""
        config = NoSQLConfig(driver="mongodb", enabled=True)
        provider = NoSQLProvider(config=config)

        mock_store = AsyncMock()
        mock_store.health_check = AsyncMock(
            side_effect=ConnectionError("db unreachable")
        )
        provider._store = mock_store

        result = await provider.health_check(timeout=1.0)

        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_health_check_timeout_error(self) -> None:
        """health_check() handles TimeoutError."""
        config = NoSQLConfig(driver="mongodb", enabled=True)
        provider = NoSQLProvider(config=config)

        mock_store = AsyncMock()
        mock_store.health_check = AsyncMock(side_effect=TimeoutError("timeout"))
        provider._store = mock_store

        result = await provider.health_check(timeout=1.0)

        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_health_check_runtime_error(self) -> None:
        """health_check() handles RuntimeError."""
        config = NoSQLConfig(driver="mongodb", enabled=True)
        provider = NoSQLProvider(config=config)

        mock_store = AsyncMock()
        mock_store.health_check = AsyncMock(side_effect=RuntimeError("runtime error"))
        provider._store = mock_store

        result = await provider.health_check(timeout=1.0)

        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_health_check_multi_backend_all_healthy(self) -> None:
        """health_check() returns HEALTHY when all multi-backend stores are healthy."""
        config = NoSQLConfig(
            backends=[
                {"name": "primary", "primary": True},
                {"name": "secondary"},
            ]
        )
        provider = NoSQLProvider(config=config)

        mock_store_1 = AsyncMock()
        mock_store_1.health_check = AsyncMock(
            return_value=HealthCheckResult(
                component="mongodb",
                status=HealthStatus.HEALTHY,
            )
        )
        mock_store_2 = AsyncMock()
        mock_store_2.health_check = AsyncMock(
            return_value=HealthCheckResult(
                component="mongodb",
                status=HealthStatus.HEALTHY,
            )
        )
        provider._store_services = [
            ("primary", mock_store_1),
            ("secondary", mock_store_2),
        ]

        result = await provider.health_check(timeout=1.0)

        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_health_check_multi_backend_one_unhealthy(self) -> None:
        """health_check() returns UNHEALTHY if any multi-backend store is unhealthy."""
        config = NoSQLConfig(
            backends=[
                {"name": "primary", "primary": True},
                {"name": "secondary"},
            ]
        )
        provider = NoSQLProvider(config=config)

        mock_store_1 = AsyncMock()
        mock_store_1.health_check = AsyncMock(
            return_value=HealthCheckResult(
                component="mongodb",
                status=HealthStatus.HEALTHY,
            )
        )
        mock_store_2 = AsyncMock()
        mock_store_2.health_check = AsyncMock(
            side_effect=ConnectionError("unreachable")
        )
        provider._store_services = [
            ("primary", mock_store_1),
            ("secondary", mock_store_2),
        ]

        result = await provider.health_check(timeout=1.0)

        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_health_check_multi_backend_degraded(self) -> None:
        """health_check() returns DEGRADED if at least one store is degraded."""
        config = NoSQLConfig(
            backends=[
                {"name": "primary", "primary": True},
                {"name": "secondary"},
            ]
        )
        provider = NoSQLProvider(config=config)

        mock_store_1 = AsyncMock()
        mock_store_1.health_check = AsyncMock(
            return_value=HealthCheckResult(
                component="mongodb",
                status=HealthStatus.HEALTHY,
            )
        )
        mock_store_2 = AsyncMock()
        mock_store_2.health_check = AsyncMock(
            return_value=HealthCheckResult(
                component="mongodb",
                status=HealthStatus.DEGRADED,
            )
        )
        provider._store_services = [
            ("primary", mock_store_1),
            ("secondary", mock_store_2),
        ]

        result = await provider.health_check(timeout=1.0)

        assert result.status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_create_store_mongodb(self) -> None:
        """_create_store returns MongoDBDocumentStore for mongodb driver."""
        config = NoSQLConfig(driver="mongodb")
        provider = NoSQLProvider()

        mock_store = MagicMock()
        with patch(
            "lexigram.nosql.di.provider.MongoDBDocumentStore", return_value=mock_store
        ) as mock_cls:
            store = provider._create_store(config)

        mock_cls.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_store_unsupported(self) -> None:
        """_create_store raises ValueError for unsupported driver."""
        config = NoSQLConfig(driver="unsupported")
        provider = NoSQLProvider()

        with pytest.raises(ValueError, match="Unsupported NoSQL driver"):
            provider._create_store(config)
