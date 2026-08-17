"""Unit tests for PromptProvider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.prompt.di.provider import PromptProvider
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.contracts.exceptions.container import UnresolvableDependencyError
from lexigram.di.provider import Provider


class TestPromptProviderStructure:
    """Test PromptProvider class structure and attributes."""

    def test_provider_class_exists(self) -> None:
        """Verify PromptProvider class exists and can be instantiated."""
        prov = PromptProvider()
        assert prov is not None
        assert isinstance(prov, PromptProvider)

    def test_provider_name(self) -> None:
        """Verify provider has correct name attribute."""
        prov = PromptProvider()
        assert prov.name == "prompt"

    def test_provider_priority(self) -> None:
        """Verify provider has DOMAIN priority."""
        prov = PromptProvider()
        assert prov.priority == ProviderPriority.DOMAIN

    def test_provider_is_provider_subclass(self) -> None:
        """Verify PromptProvider is a proper Provider subclass."""
        assert issubclass(PromptProvider, Provider)

    def test_provider_has_required_methods(self) -> None:
        """Verify provider has all required lifecycle methods."""
        prov = PromptProvider()
        assert hasattr(prov, "register")
        assert callable(prov.register)
        assert hasattr(prov, "boot")
        assert callable(prov.boot)
        assert hasattr(prov, "shutdown")
        assert callable(prov.shutdown)


class TestPromptProviderLifecycle:
    """Test PromptProvider lifecycle methods."""

    @pytest.mark.asyncio
    async def test_register_method_signature(self) -> None:
        """Verify register() method has correct async signature."""
        prov = PromptProvider()
        container = MagicMock()
        container.singleton = MagicMock()

        # Should complete without error
        await prov.register(container)

    @pytest.mark.asyncio
    async def test_boot_method_signature(self) -> None:
        """Verify boot() method has correct async signature."""
        from lexigram.ai.prompt.service.service import PromptService

        prov = PromptProvider()
        container = MagicMock()
        # Mock resolve_optional to return no hook registry
        container.resolve_optional = AsyncMock(return_value=None)
        # Mock resolve to return a service, but raise for the optional token counter
        def _resolve(cls: object) -> object:
            if cls.__name__ == "TokenCounterProtocol":
                raise UnresolvableDependencyError("TokenCounterProtocol not available")
            return PromptService([])

        container.resolve = AsyncMock(side_effect=_resolve)

        # Should complete without error
        await prov.boot(container)

    @pytest.mark.asyncio
    async def test_shutdown_method_signature(self) -> None:
        """Verify shutdown() method has correct async signature."""
        prov = PromptProvider()

        # Should complete without error
        await prov.shutdown()
