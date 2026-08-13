"""Tests for the GraphProvider tenancy wiring."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGraphProviderTenancyWiring:
    """Tests for GraphProvider._maybe_wrap_with_tenancy."""

    @pytest.fixture
    def mock_container(self) -> MagicMock:
        c = MagicMock()
        c.resolve = AsyncMock()
        return c

    def _make_provider(self, enabled: bool = False, strategy: str = "node_property") -> MagicMock:
        from lexigram.graph.config import GraphTenancyConfig
        from lexigram.graph.di.provider import GraphProvider

        config = MagicMock()
        config.tenancy = GraphTenancyConfig(enabled=enabled, strategy=strategy)
        config.backend = "memory"
        config.enabled = True

        provider = GraphProvider(config=config)
        return provider

    @pytest.mark.asyncio
    async def test_wrapping_disabled_returns_store_unchanged(self, mock_container) -> None:
        provider = self._make_provider(enabled=False)
        store = MagicMock()
        result = await provider._maybe_wrap_with_tenancy(store, mock_container)
        assert result is store
        mock_container.resolve.assert_not_called()

    @pytest.mark.asyncio
    async def test_wrapping_graph_per_tenant_strategy(self, mock_container) -> None:
        from lexigram.graph.tenancy.decorator import TenantGraphStoreDecorator

        provider = self._make_provider(enabled=True, strategy="graph_per_tenant")

        mock_ctx = MagicMock()
        mock_container.resolve.return_value = mock_ctx

        store = MagicMock()
        result = await provider._maybe_wrap_with_tenancy(store, mock_container)
        assert isinstance(result, TenantGraphStoreDecorator)

    @pytest.mark.asyncio
    async def test_wrapping_node_property_strategy(self, mock_container) -> None:
        from lexigram.graph.tenancy.decorator import TenantGraphStoreDecorator

        provider = self._make_provider(enabled=True, strategy="node_property")

        mock_ctx = MagicMock()
        mock_container.resolve.return_value = mock_ctx

        store = MagicMock()
        result = await provider._maybe_wrap_with_tenancy(store, mock_container)
        assert isinstance(result, TenantGraphStoreDecorator)

    @pytest.mark.asyncio
    async def test_boot_wraps_store_when_tenancy_enabled(self) -> None:
        from lexigram.graph.config import GraphTenancyConfig
        from lexigram.graph.di.provider import GraphProvider

        config = MagicMock()
        config.tenancy = GraphTenancyConfig(enabled=True, strategy="graph_per_tenant")
        config.backend = "memory"
        config.enabled = True

        provider = GraphProvider(config=config)
        provider._maybe_wrap_with_tenancy = AsyncMock()  # type: ignore[method-assign]

        mock_container = MagicMock()
        mock_store = MagicMock()
        mock_container.resolve = AsyncMock(return_value=mock_store)
        mock_store.connect = AsyncMock()

        wrapped_store = MagicMock()
        provider._maybe_wrap_with_tenancy.return_value = wrapped_store

        await provider.boot(mock_container)
        provider._maybe_wrap_with_tenancy.assert_awaited_once_with(mock_store, mock_container)
        assert provider._store is wrapped_store

    @pytest.mark.asyncio
    async def test_boot_skips_wrapping_when_tenancy_disabled(self) -> None:
        from lexigram.graph.config import GraphTenancyConfig
        from lexigram.graph.di.provider import GraphProvider

        config = MagicMock()
        config.tenancy = GraphTenancyConfig(enabled=False, strategy="node_property")
        config.backend = "memory"
        config.enabled = True

        provider = GraphProvider(config=config)

        mock_container = MagicMock()
        mock_store = MagicMock()
        mock_container.resolve = AsyncMock(return_value=mock_store)
        mock_store.connect = AsyncMock()

        await provider.boot(mock_container)
        assert isinstance(provider._store, MagicMock)
        # store should be the raw store, not wrapped
        assert provider._store is mock_store
