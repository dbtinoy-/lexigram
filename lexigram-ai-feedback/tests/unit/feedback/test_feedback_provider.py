"""Unit tests for FeedbackProvider."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from lexigram.ai.feedback.di.provider import FeedbackProvider
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.di.provider import Provider


class TestFeedbackProviderStructure:
    """Test FeedbackProvider class structure and attributes."""

    def test_provider_class_exists(self) -> None:
        """Verify FeedbackProvider class exists and can be instantiated."""
        prov = FeedbackProvider()
        assert prov is not None
        assert isinstance(prov, FeedbackProvider)

    def test_provider_name(self) -> None:
        """Verify provider has correct name attribute."""
        prov = FeedbackProvider()
        assert prov.name == "feedback"

    def test_provider_priority(self) -> None:
        """Verify provider has DOMAIN priority."""
        prov = FeedbackProvider()
        assert prov.priority == ProviderPriority.DOMAIN

    def test_provider_is_provider_subclass(self) -> None:
        """Verify FeedbackProvider is a proper Provider subclass."""
        assert issubclass(FeedbackProvider, Provider)

    def test_provider_has_required_methods(self) -> None:
        """Verify provider has all required lifecycle methods."""
        prov = FeedbackProvider()
        assert hasattr(prov, "register")
        assert callable(prov.register)
        assert hasattr(prov, "boot")
        assert callable(prov.boot)
        assert hasattr(prov, "shutdown")
        assert callable(prov.shutdown)


class TestFeedbackProviderLifecycle:
    """Test FeedbackProvider lifecycle methods."""

    @pytest.mark.asyncio
    async def test_register_method_signature(self) -> None:
        """Verify register() method has correct async signature."""
        prov = FeedbackProvider()
        container = MagicMock()
        container.singleton = MagicMock()

        # Should complete without error
        await prov.register(container)

    @pytest.mark.asyncio
    async def test_boot_method_signature(self) -> None:
        """Verify boot() method has correct async signature."""
        prov = FeedbackProvider()
        container = MagicMock()
        container.resolve_optional = AsyncMock()

        # Should complete without error
        await prov.boot(container)

    @pytest.mark.asyncio
    async def test_shutdown_method_signature(self) -> None:
        """Verify shutdown() method has correct async signature."""
        prov = FeedbackProvider()

        # Should complete without error
        await prov.shutdown()
