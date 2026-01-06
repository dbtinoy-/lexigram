"""Unit tests for LLMProvider."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from lexigram.ai.llm.di.provider import LLMProvider
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.di.provider import Provider


class TestLLMProviderStructure:
    """Test LLMProvider class structure and attributes."""

    def test_provider_class_exists(self) -> None:
        """Verify LLMProvider class exists and can be instantiated."""
        prov = LLMProvider()
        assert prov is not None
        assert isinstance(prov, LLMProvider)

    def test_provider_name(self) -> None:
        """Verify provider has correct name attribute."""
        prov = LLMProvider()
        assert prov.name == "llm"

    def test_provider_priority(self) -> None:
        """Verify provider has DOMAIN priority."""
        prov = LLMProvider()
        assert prov.priority == ProviderPriority.DOMAIN

    def test_provider_is_provider_subclass(self) -> None:
        """Verify LLMProvider is a proper Provider subclass."""
        assert issubclass(LLMProvider, Provider)

    def test_provider_has_required_methods(self) -> None:
        """Verify provider has all required lifecycle methods."""
        prov = LLMProvider()
        assert hasattr(prov, "register")
        assert callable(prov.register)
        assert hasattr(prov, "boot")
        assert callable(prov.boot)
        assert hasattr(prov, "shutdown")
        assert callable(prov.shutdown)


class TestLLMProviderLifecycle:
    """Test LLMProvider lifecycle methods."""

    @pytest.mark.asyncio
    async def test_register_method_signature(self) -> None:
        """Verify register() method has correct async signature."""
        prov = LLMProvider()
        container = MagicMock()
        container.singleton = MagicMock()

        # Should complete without error
        await prov.register(container)

    @pytest.mark.asyncio
    async def test_boot_method_signature(self) -> None:
        """Verify boot() method has correct async signature."""
        prov = LLMProvider()
        container = MagicMock()
        container.resolve = AsyncMock()
        container.resolve_optional = AsyncMock()

        # Should complete without error
        await prov.boot(container)

    @pytest.mark.asyncio
    async def test_shutdown_method_signature(self) -> None:
        """Verify shutdown() method has correct async signature."""
        prov = LLMProvider()

        # Should complete without error
        await prov.shutdown()
