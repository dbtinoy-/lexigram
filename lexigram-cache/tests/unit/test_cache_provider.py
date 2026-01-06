"""Tests for cache provider module"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.cache.di import provider
from lexigram.cache.di.provider import CacheProvider
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.di.provider import Provider
from lexigram.testing.clock import FixedClock


class TestCacheProviderModule:
    """Test the cache provider module exports and lazy loading"""

    def test_provider_module_imports(self) -> None:
        """Test that provider module can be imported"""
        assert provider is not None

    def test_provider_module_has_all_exports(self) -> None:
        """Test that provider module has all expected exports in __all__"""
        expected_exports = [
            "CacheProvider",
        ]

        assert hasattr(provider, "__all__")
        assert set(provider.__all__) == set(expected_exports)

    def test_provider_lazy_loading_cache_service(self) -> None:
        """Test lazy loading of CacheService"""
        cache_service = provider.CacheService
        assert cache_service is not None

    def test_provider_lazy_loading_cache_provider(self) -> None:
        """Test lazy loading of CacheProvider"""
        cache_provider = provider.CacheProvider
        assert cache_provider is not None

    def test_provider_invalid_attribute_raises_attribute_error(self) -> None:
        """Test that accessing invalid attribute raises AttributeError"""
        with pytest.raises(
            AttributeError, match=r"module .* has no attribute 'InvalidAttribute'",
        ):
            _ = provider.InvalidAttribute

    def test_provider_direct_imports_available(self) -> None:
        """Test that CacheProvider is available"""
        assert hasattr(provider, "CacheProvider")


class TestCacheProviderStructure:
    """Test CacheProvider class structure and attributes."""

    def test_provider_class_exists(self) -> None:
        """Verify CacheProvider class exists and can be instantiated."""
        prov = CacheProvider()
        assert prov is not None
        assert isinstance(prov, CacheProvider)

    def test_provider_name(self) -> None:
        """Verify provider has correct name attribute."""
        prov = CacheProvider()
        assert prov.name == "cache"

    def test_provider_priority(self) -> None:
        """Verify provider has INFRASTRUCTURE priority."""
        prov = CacheProvider()
        assert prov.priority == ProviderPriority.INFRASTRUCTURE

    def test_provider_is_provider_subclass(self) -> None:
        """Verify CacheProvider is a proper Provider subclass."""
        assert issubclass(CacheProvider, Provider)

    def test_provider_has_register_method(self) -> None:
        """Verify provider has async register method."""
        prov = CacheProvider()
        assert hasattr(prov, "register")
        assert callable(prov.register)

    def test_provider_has_boot_method(self) -> None:
        """Verify provider has async boot method."""
        prov = CacheProvider()
        assert hasattr(prov, "boot")
        assert callable(prov.boot)

    def test_provider_has_shutdown_method(self) -> None:
        """Verify provider has async shutdown method."""
        prov = CacheProvider()
        assert hasattr(prov, "shutdown")
        assert callable(prov.shutdown)


class TestCacheProviderMethods:
    """Test CacheProvider method signatures and lifecycle."""

    @pytest.mark.asyncio
    async def test_register_method_signature(self) -> None:
        """Verify register() method has correct async signature."""
        prov = CacheProvider()
        container = MagicMock()
        container.singleton = MagicMock()

        # Should complete without error
        await prov.register(container)

    @pytest.mark.asyncio
    async def test_boot_method_signature(self) -> None:
        """Verify boot() method has correct async signature."""
        prov = CacheProvider()
        container = MagicMock()
        container.resolve = AsyncMock()
        container.resolve_optional = AsyncMock()

        # Should complete without error
        await prov.boot(container)

    @pytest.mark.asyncio
    async def test_shutdown_method_signature(self) -> None:
        """Verify shutdown() method has correct async signature."""
        prov = CacheProvider()

        # Should complete without error
        await prov.shutdown()

    @pytest.fixture
    def clock(self):
        return FixedClock()

    @pytest.mark.asyncio
    async def test_boot_wires_registered_repository_pairs(self, clock) -> None:
        """Verify boot wires queued cache repository observation pairs."""
        provider = CacheProvider()
        provider._initialize_backends = AsyncMock()
        provider._initialize_services = MagicMock()

        cache_repository = MagicMock()
        source_repository = MagicMock()

        provider.observe_repository(cache_repository, source_repository)

        container = MagicMock()
        container.resolve = AsyncMock(return_value=clock)
        await provider.boot(container)

        cache_repository.observe.assert_called_once_with(source_repository)
