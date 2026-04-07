"""Tests for audit DI providers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.audit.di.sub_providers.core_provider import AuditCoreProvider
from lexigram.contracts.audit import AuditLoggerProtocol, AuditStoreProtocol


class MockContainerRegistrar:
    """Mock container registrar."""
    def __init__(self):
        self.bindings = {}

    def singleton(self, protocol, impl):
        self.bindings[(protocol, "singleton")] = impl


class MockContainerResolver:
    """Mock container resolver."""
    def __init__(self, resolution_map: dict = None):
        self.resolution_map = resolution_map or {}

    async def resolve(self, protocol):
        return self.resolution_map.get(protocol)


class TestAuditCoreProvider:
    """Tests for AuditCoreProvider."""

    def test_provider_creation(self) -> None:
        provider = AuditCoreProvider()
        assert provider.name == "audit_core"
        assert provider.priority is not None

    def test_provider_with_config(self) -> None:
        from lexigram.audit.config import AuditConfig
        config = AuditConfig(store_backend="memory")
        provider = AuditCoreProvider(config=config)
        assert provider._config is config

    @pytest.mark.asyncio
    async def test_register_binds_store_and_logger(self) -> None:
        provider = AuditCoreProvider()
        container = MockContainerRegistrar()
        
        await provider.register(container)
        
        assert (AuditStoreProtocol, "singleton") in container.bindings
        assert (AuditLoggerProtocol, "singleton") in container.bindings

    @pytest.mark.asyncio
    async def test_register_with_memory_backend(self) -> None:
        from lexigram.audit.config import AuditConfig
        config = AuditConfig(store_backend="memory")
        provider = AuditCoreProvider(config=config)
        container = MockContainerRegistrar()
        
        await provider.register(container)
        
        # Should use InMemoryAuditStore
        impl = container.bindings.get((AuditStoreProtocol, "singleton"))
        assert impl is not None

    @pytest.mark.asyncio
    async def test_boot_initializes_store(self) -> None:
        mock_store = MagicMock()
        mock_store.initialize = AsyncMock()
        
        provider = AuditCoreProvider()
        container = MockContainerResolver({AuditStoreProtocol: mock_store})
        
        await provider.boot(container)
        
        mock_store.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_boot_handles_no_initialize(self) -> None:
        mock_store = MagicMock()
        del mock_store.initialize  # No initialize method
        
        provider = AuditCoreProvider()
        container = MockContainerResolver({AuditStoreProtocol: mock_store})
        
        # Should not raise
        await provider.boot(container)