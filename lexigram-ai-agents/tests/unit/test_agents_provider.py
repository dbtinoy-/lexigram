"""Unit tests for AgentsProvider."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from lexigram.ai.agents.di.provider import AgentsProvider
from lexigram.ai.agents.tools import tool
from lexigram.ai.agents.tools.registry import ToolRegistryImpl
from lexigram.contracts.ai import ToolRegistryProtocol
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.di.container import Container
from lexigram.di.provider import Provider


class TestAgentsProviderStructure:
    """Test AgentsProvider class structure and attributes."""

    def test_provider_class_exists(self) -> None:
        """Verify AgentsProvider class exists and can be instantiated."""
        prov = AgentsProvider()
        assert prov is not None
        assert isinstance(prov, AgentsProvider)

    def test_provider_name(self) -> None:
        """Verify provider has correct name attribute."""
        prov = AgentsProvider()
        assert prov.name == "ai-agents"

    def test_provider_priority(self) -> None:
        """Verify provider has DOMAIN priority."""
        prov = AgentsProvider()
        assert prov.priority == ProviderPriority.DOMAIN

    def test_provider_is_provider_subclass(self) -> None:
        """Verify AgentsProvider is a proper Provider subclass."""
        assert issubclass(AgentsProvider, Provider)

    def test_provider_has_required_methods(self) -> None:
        """Verify provider has all required lifecycle methods."""
        prov = AgentsProvider()
        assert hasattr(prov, "register")
        assert callable(prov.register)
        assert hasattr(prov, "boot")
        assert callable(prov.boot)
        assert hasattr(prov, "shutdown")
        assert callable(prov.shutdown)


class TestAgentsProviderLifecycle:
    """Test AgentsProvider lifecycle methods."""

    @pytest.mark.asyncio
    async def test_register_method_signature(self) -> None:
        """Verify register() method has correct async signature."""
        prov = AgentsProvider()
        container = MagicMock()
        container.singleton = MagicMock()

        # Should complete without error
        await prov.register(container)

    @pytest.mark.asyncio
    async def test_boot_method_signature(self) -> None:
        """Verify boot() method has correct async signature."""
        prov = AgentsProvider()
        container = MagicMock()
        container.resolve = AsyncMock()
        container.resolve_optional = AsyncMock()

        # Should complete without error
        await prov.boot(container)

    @pytest.mark.asyncio
    async def test_shutdown_method_signature(self) -> None:
        """Verify shutdown() method has correct async signature."""
        prov = AgentsProvider()

        # Should complete without error
        await prov.shutdown()

class TestAgentsProviderDITokens:
    """Regression tests for DI token aliasing in AgentsProvider."""

    @pytest.mark.asyncio
    async def test_tool_registry_protocol_and_impl_resolve_same_singleton(self) -> None:
        """ToolRegistryProtocol and ToolRegistryImpl resolve to one shared instance."""
        prov = AgentsProvider()
        container = Container()

        await prov.register(container)

        registry_impl = await container.resolve(ToolRegistryImpl)
        registry_protocol = await container.resolve(ToolRegistryProtocol)

        assert registry_impl is registry_protocol

        @tool
        async def ping() -> str:
            """Ping test tool."""
            return "pong"

        registry_impl.register(ping)

        assert registry_protocol.get("ping") is ping
        assert any(item.name == "ping" for item in registry_protocol.list_tools())

