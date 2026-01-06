"""Unit tests for SkillsProvider."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from lexigram.ai.skills.di.provider import SkillsProvider
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.di.provider import Provider


class TestSkillsProviderStructure:
    """Test SkillsProvider class structure and attributes."""

    def test_provider_class_exists(self) -> None:
        """Verify SkillsProvider class exists and can be instantiated."""
        prov = SkillsProvider()
        assert prov is not None
        assert isinstance(prov, SkillsProvider)

    def test_provider_name(self) -> None:
        """Verify provider has correct name attribute."""
        prov = SkillsProvider()
        assert prov.name == "skills"

    def test_provider_priority(self) -> None:
        """Verify provider has DOMAIN priority."""
        prov = SkillsProvider()
        assert prov.priority == ProviderPriority.DOMAIN

    def test_provider_is_provider_subclass(self) -> None:
        """Verify SkillsProvider is a proper Provider subclass."""
        assert issubclass(SkillsProvider, Provider)

    def test_provider_has_required_methods(self) -> None:
        """Verify provider has all required lifecycle methods."""
        prov = SkillsProvider()
        assert hasattr(prov, "register")
        assert callable(prov.register)
        assert hasattr(prov, "boot")
        assert callable(prov.boot)
        assert hasattr(prov, "shutdown")
        assert callable(prov.shutdown)


class TestSkillsProviderLifecycle:
    """Test SkillsProvider lifecycle methods."""

    @pytest.mark.asyncio
    async def test_register_method_signature(self) -> None:
        """Verify register() method has correct async signature."""
        prov = SkillsProvider()
        container = MagicMock()
        container.singleton = MagicMock()

        # Should complete without error
        await prov.register(container)

    @pytest.mark.asyncio
    async def test_boot_method_signature(self) -> None:
        """Verify boot() method has correct async signature."""
        prov = SkillsProvider()
        container = MagicMock()
        container.resolve_optional = AsyncMock()

        # Should complete without error
        await prov.boot(container)

    @pytest.mark.asyncio
    async def test_shutdown_method_signature(self) -> None:
        """Verify shutdown() method has correct async signature."""
        prov = SkillsProvider()

        # Should complete without error
        await prov.shutdown()
