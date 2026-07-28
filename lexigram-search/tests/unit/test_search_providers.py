"""Tests for SearchProvider core functionality."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.search.config import (
    BackendType,
    MeiliSearchConfig,
    SearchConfig,
    SQLiteSearchConfig,
)
from lexigram.search.di.provider import SearchProvider


class TestSearchProviderConfigure:
    """Tests for SearchProvider.configure()."""

    def test_configure_meilisearch_backend(self) -> None:
        """configure() creates a MeiliSearchBackend when backend_type is MEILISEARCH."""
        config = SearchConfig(
            backend_type=BackendType.MEILISEARCH,
            meilisearch=MeiliSearchConfig(
                api_url="http://localhost:7700",
                api_key="test-key",
            ),
        )
        provider = SearchProvider.configure(config)

        assert provider is not None
        assert provider.backend is not None
        assert provider.backend.__class__.__name__ == "MeiliSearchBackend"

    def test_configure_memory_backend(self) -> None:
        """configure() creates a NullBackend when backend_type is MEMORY."""
        config = SearchConfig(backend_type=BackendType.MEMORY)
        provider = SearchProvider.configure(config)

        assert provider is not None
        assert provider.backend.__class__.__name__ == "NullBackend"
        assert provider._uses_db_backend is False

    def test_configure_sqlite_backend(self) -> None:
        """configure() creates a SQLiteSearchBackend when backend_type is SQLITE."""
        config = SearchConfig(
            backend_type=BackendType.SQLITE,
            sqlite=SQLiteSearchConfig(db_path=":memory:"),
        )
        provider = SearchProvider.configure(config)

        assert provider is not None
        assert provider.backend.__class__.__name__ == "SQLiteSearchBackend"
        assert provider._uses_db_backend is False

    def test_configure_postgres_placeholder_backend(self) -> None:
        """configure() creates a placeholder for POSTGRES backend since it needs DB."""
        from lexigram.search.config import PostgresSearchConfig

        config = SearchConfig(
            backend_type=BackendType.POSTGRES,
            postgres=PostgresSearchConfig(connection_string="postgresql://user:pass@localhost/db"),
        )
        provider = SearchProvider.configure(config)

        assert provider._uses_db_backend is True
        assert provider.backend.__class__.__name__ == "NullBackend"

    def test_configure_mysql_placeholder_backend(self) -> None:
        """configure() creates a placeholder for MYSQL backend since it needs DB."""
        from lexigram.search.config import MySQLSearchConfig

        config = SearchConfig(
            backend_type=BackendType.MYSQL,
            mysql=MySQLSearchConfig(connection_string="mysql://user:pass@localhost/db"),
        )
        provider = SearchProvider.configure(config)

        assert provider._uses_db_backend is True
        assert provider.backend.__class__.__name__ == "NullBackend"

    def test_configure_invalid_backend_raises(self) -> None:
        """configure() raises ValueError for unsupported backend types."""
        config = MagicMock(spec=SearchConfig)
        config.backend_type = "invalid_type"

        with pytest.raises(ValueError, match="Unsupported backend type"):
            SearchProvider.configure(config)


class TestSearchProviderFromConfig:
    """Tests for SearchProvider.from_config()."""

    def test_from_config_returns_provider(self) -> None:
        """from_config() returns a configured SearchProvider."""
        config = SearchConfig(backend_type=BackendType.MEMORY)
        provider = SearchProvider.from_config(config)

        assert provider is not None
        assert provider._config is config

    def test_from_config_preserves_config(self) -> None:
        """from_config() preserves the SearchConfig on the provider."""
        config = SearchConfig(
            enabled=True,
            backend_type=BackendType.MEILISEARCH,
            meilisearch=MeiliSearchConfig(api_url="http://localhost:7700"),
        )
        provider = SearchProvider.from_config(config)

        assert provider._config is config


class TestSearchProviderFactoryMethods:
    """Tests for SearchProvider factory methods."""

    def test_with_memory(self) -> None:
        """with_memory() creates a provider with NullBackend."""
        provider = SearchProvider.with_memory()

        assert provider.backend.__class__.__name__ == "NullBackend"

    def test_with_meilisearch_default_url(self) -> None:
        """with_meilisearch() uses default URL when not specified."""
        provider = SearchProvider.with_meilisearch()

        assert provider.backend.url == "http://localhost:7700"

    def test_with_meilisearch_custom_url(self) -> None:
        """with_meilisearch() accepts custom URL and API key."""
        provider = SearchProvider.with_meilisearch(
            url="http://custom:7700",
            api_key="custom-key",
        )

        assert provider.backend.url == "http://custom:7700"
        assert provider.backend.api_key == "custom-key"


class TestSearchProviderSingleBackendRegister:
    """Tests for SearchProvider single-backend registration."""

    @pytest.mark.asyncio
    async def test_register_single_backend(self) -> None:
        """register() registers SearchProvider and SearchEngine as singletons."""
        provider = SearchProvider.with_memory()
        container = MagicMock()
        container.singleton = MagicMock()

        await provider.register(container)

        singleton_calls = container.singleton.call_args_list
        registered_types = [c.args[0] for c in singleton_calls]

        assert SearchProvider in registered_types
        from lexigram.search.engine import SearchEngine

        assert SearchEngine in registered_types

    @pytest.mark.asyncio
    async def test_register_disabled_config_skips_registration(self) -> None:
        """register() skips registration when config.enabled is False."""
        config = SearchConfig(enabled=False, backend_type=BackendType.MEMORY)
        provider = SearchProvider.configure(config)
        provider._search_services = []
        container = MagicMock()
        container.singleton = MagicMock()

        await provider.register(container)

        # When enabled=False, _search_services stays empty and no singletons registered
        assert provider._search_services == []


class TestSearchProviderBoot:
    """Tests for SearchProvider.boot()."""

    @pytest.fixture
    def mock_container(self) -> MagicMock:
        container = MagicMock()
        container.resolve = AsyncMock()
        return container

    @pytest.mark.asyncio
    async def test_boot_single_backend_healthy(self, mock_container: MagicMock) -> None:
        """boot() succeeds when backend is healthy."""
        provider = SearchProvider.with_memory()
        provider._search_services = []

        healthy_backend = AsyncMock()
        healthy_backend.health_check = AsyncMock(
            return_value=HealthCheckResult(
                component="search",
                status=HealthStatus.HEALTHY,
                duration_ms=1.0,
            )
        )
        provider.backend = healthy_backend

        await provider.boot(mock_container)

        healthy_backend.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_boot_single_backend_unhealthy_raises(self, mock_container: MagicMock) -> None:
        """boot() raises RuntimeError when backend is unhealthy."""
        provider = SearchProvider.with_memory()
        provider._search_services = []

        unhealthy_backend = AsyncMock()
        unhealthy_backend.health_check = AsyncMock(
            return_value=HealthCheckResult(
                component="search",
                status=HealthStatus.UNHEALTHY,
                error="connection refused",
                duration_ms=1.0,
            )
        )
        provider.backend = unhealthy_backend

        with pytest.raises(RuntimeError, match="unhealthy at startup"):
            await provider.boot(mock_container)

    @pytest.mark.asyncio
    async def test_boot_disabled_config_returns_early(self, mock_container: MagicMock) -> None:
        """boot() returns early when config.enabled is False."""
        config = SearchConfig(enabled=False, backend_type=BackendType.MEMORY)
        provider = SearchProvider.configure(config)

        await provider.boot(mock_container)

        mock_container.resolve.assert_not_called()


class TestSearchProviderHealthCheck:
    """Tests for SearchProvider.health_check()."""

    @pytest.mark.asyncio
    async def test_health_check_single_healthy(self) -> None:
        """health_check() returns HEALTHY for healthy single backend."""
        provider = SearchProvider.with_memory()
        provider._search_services = []

        healthy_backend = AsyncMock()
        healthy_backend.health_check = AsyncMock(
            return_value=HealthCheckResult(
                component="search",
                status=HealthStatus.HEALTHY,
                duration_ms=1.0,
            )
        )
        provider.backend = healthy_backend

        result = await provider.health_check()

        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_health_check_single_unhealthy(self) -> None:
        """health_check() returns UNHEALTHY for unhealthy single backend."""
        provider = SearchProvider.with_memory()
        provider._search_services = []

        unhealthy_backend = AsyncMock()
        unhealthy_backend.health_check = AsyncMock(
            return_value=HealthCheckResult(
                component="search",
                status=HealthStatus.UNHEALTHY,
                error="connection refused",
                duration_ms=1.0,
            )
        )
        provider.backend = unhealthy_backend

        result = await provider.health_check()

        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_health_check_exception_returns_unhealthy(self) -> None:
        """health_check() returns UNHEALTHY when exception occurs."""
        provider = SearchProvider.with_memory()
        provider._search_services = []

        failing_backend = AsyncMock()
        failing_backend.health_check = AsyncMock(
            side_effect=RuntimeError("connection failed")
        )
        failing_backend.__class__ = MagicMock()
        failing_backend.__class__.__name__ = "FailingBackend"
        provider.backend = failing_backend

        result = await provider.health_check()

        assert result.status == HealthStatus.UNHEALTHY
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_health_check_single_returns_result_with_component(self) -> None:
        """health_check() returns result with correct component."""
        provider = SearchProvider.with_memory()
        provider._search_services = []

        backend = AsyncMock()
        backend.health_check = AsyncMock(
            return_value=HealthCheckResult(
                component="search",
                status=HealthStatus.HEALTHY,
                duration_ms=1.0,
            )
        )
        provider.backend = backend

        result = await provider.health_check()

        assert result.component == "search"
        assert result.status == HealthStatus.HEALTHY


class TestSearchProviderShutdown:
    """Tests for SearchProvider.shutdown()."""

    @pytest.mark.asyncio
    async def test_shutdown_multi_backend_calls_close(self) -> None:
        """shutdown() closes backends in multi-backend mode."""
        config = SearchConfig(
            backends=[
                MagicMock(name="alpha", backend_type=BackendType.MEMORY),
                MagicMock(name="beta", backend_type=BackendType.MEMORY),
            ]
        )
        provider = SearchProvider.from_config(config)
        container = MagicMock()
        await provider.register(container)

        close_calls: list[str] = []
        for idx, (name, backend) in enumerate(provider._search_services):
            mock = AsyncMock()
            mock.close = AsyncMock(side_effect=lambda n=name: close_calls.append(n))
            provider._search_services[idx] = (name, mock)

        await provider.shutdown()

        assert len(close_calls) == 2

    @pytest.mark.asyncio
    async def test_shutdown_single_backend_no_services_no_op(self) -> None:
        """shutdown() with empty _search_services does nothing for single-backend."""
        provider = SearchProvider.with_memory()
        provider._search_services = []

        await provider.shutdown()  # should not raise


class TestSearchProviderPriority:
    """Tests for SearchProvider priority and metadata."""

    def test_provider_has_name(self) -> None:
        """SearchProvider has name 'search'."""
        provider = SearchProvider.with_memory()

        assert provider.name == "search"

    def test_provider_has_priority(self) -> None:
        """SearchProvider has DOMAIN priority."""
        provider = SearchProvider.with_memory()

        assert provider.priority == ProviderPriority.DOMAIN

    def test_provider_has_config_key(self) -> None:
        """SearchProvider has config_key 'search'."""
        provider = SearchProvider.with_memory()

        assert provider.config_key == "search"

    def test_provider_has_config_model(self) -> None:
        """SearchProvider has config_model set to SearchConfig."""
        provider = SearchProvider.with_memory()

        assert provider.config_model is SearchConfig


from lexigram.contracts.core import ProviderPriority