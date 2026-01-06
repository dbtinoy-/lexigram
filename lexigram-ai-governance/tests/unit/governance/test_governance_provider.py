"""Unit tests for GovernanceProvider."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from lexigram.ai.governance.di.provider import GovernanceProvider
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.di.provider import Provider


class TestGovernanceProviderStructure:
    """Test GovernanceProvider class structure and attributes."""

    def test_provider_class_exists(self) -> None:
        """Verify GovernanceProvider class exists and can be instantiated."""
        prov = GovernanceProvider()
        assert prov is not None
        assert isinstance(prov, GovernanceProvider)

    def test_provider_name(self) -> None:
        """Verify provider has correct name attribute."""
        prov = GovernanceProvider()
        assert prov.name == "governance"

    def test_provider_priority(self) -> None:
        """Verify provider has DOMAIN priority."""
        prov = GovernanceProvider()
        assert prov.priority == ProviderPriority.DOMAIN

    def test_provider_is_provider_subclass(self) -> None:
        """Verify GovernanceProvider is a proper Provider subclass."""
        assert issubclass(GovernanceProvider, Provider)

    def test_provider_has_required_methods(self) -> None:
        """Verify provider has all required lifecycle methods."""
        prov = GovernanceProvider()
        assert hasattr(prov, "register")
        assert callable(prov.register)
        assert hasattr(prov, "boot")
        assert callable(prov.boot)
        assert hasattr(prov, "shutdown")
        assert callable(prov.shutdown)


class TestGovernanceProviderLifecycle:
    """Test GovernanceProvider lifecycle methods."""

    @pytest.mark.asyncio
    async def test_register_method_signature(self) -> None:
        """Verify register() method has correct async signature."""
        prov = GovernanceProvider()
        container = MagicMock()
        container.singleton = MagicMock()

        # Should complete without error
        await prov.register(container)

    @pytest.mark.asyncio
    async def test_boot_method_signature(self) -> None:
        """Verify boot() method has correct async signature."""
        prov = GovernanceProvider()
        container = MagicMock()

        # Should complete without error
        await prov.boot(container)

    @pytest.mark.asyncio
    async def test_shutdown_method_signature(self) -> None:
        """Verify shutdown() method has correct async signature."""
        prov = GovernanceProvider()

        # Should complete without error
        await prov.shutdown()
