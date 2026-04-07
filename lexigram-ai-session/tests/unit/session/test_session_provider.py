"""Unit tests for SessionProvider."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from lexigram.ai.session.di.provider import SessionProvider
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.di.provider import Provider


class TestSessionProviderStructure:
    """Test SessionProvider class structure and attributes."""

    def test_provider_class_exists(self) -> None:
        """Verify SessionProvider class exists and can be instantiated."""
        prov = SessionProvider()
        assert prov is not None
        assert isinstance(prov, SessionProvider)

    def test_provider_name(self) -> None:
        """Verify provider has correct name attribute."""
        prov = SessionProvider()
        assert prov.name == "session"

    def test_provider_priority(self) -> None:
        """Verify provider has INFRASTRUCTURE priority."""
        prov = SessionProvider()
        assert prov.priority == ProviderPriority.INFRASTRUCTURE

    def test_provider_is_provider_subclass(self) -> None:
        """Verify SessionProvider is a proper Provider subclass."""
        assert issubclass(SessionProvider, Provider)

    def test_provider_has_required_methods(self) -> None:
        """Verify provider has all required lifecycle methods."""
        prov = SessionProvider()
        assert hasattr(prov, "register")
        assert callable(prov.register)
        assert hasattr(prov, "boot")
        assert callable(prov.boot)
        assert hasattr(prov, "shutdown")
        assert callable(prov.shutdown)


class TestSessionProviderLifecycle:
    """Test SessionProvider lifecycle methods."""

    @pytest.mark.asyncio
    async def test_register_method_signature(self) -> None:
        """Verify register() method has correct async signature."""
        prov = SessionProvider()
        container = MagicMock()
        container.singleton = MagicMock()

        # Should complete without error
        await prov.register(container)

    @pytest.mark.asyncio
    async def test_boot_method_signature(self) -> None:
        """Verify boot() method has correct async signature."""
        prov = SessionProvider()
        container = MagicMock()
        container.resolve = AsyncMock()

        # Should complete without error
        await prov.boot(container)

    @pytest.mark.asyncio
    async def test_shutdown_method_signature(self) -> None:
        """Verify shutdown() method has correct async signature."""
        prov = SessionProvider()

        # Should complete without error
        await prov.shutdown()
