"""Unit tests for {{ class_name }}Provider."""
from __future__ import annotations

import pytest

from lexigram.{{ package_name }}.di.provider import {{ class_name }}Provider


class Test{{ class_name }}Provider:
    """Tests for the {{ class_name }}Provider."""

    @pytest.mark.asyncio
    async def test_provider_has_expected_name(self) -> None:
        """{{ class_name }}Provider.name is the package slug."""
        provider = {{ class_name }}Provider()
        assert provider.name == "{{ package_name }}"

    @pytest.mark.asyncio
    async def test_register_does_not_raise(self) -> None:
        """register() should complete without errors on an empty container."""
        from unittest.mock import AsyncMock, MagicMock

        provider = {{ class_name }}Provider()
        mock_container = MagicMock()
        mock_container.singleton = MagicMock()
        mock_container.transient = MagicMock()
        await provider.register(mock_container)

    @pytest.mark.asyncio
    async def test_shutdown_does_not_raise(self) -> None:
        """shutdown() should complete without errors."""
        provider = {{ class_name }}Provider()
        await provider.shutdown()
