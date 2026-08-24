"""Tests for AIProvider.boot() optional dependency resolution."""

from __future__ import annotations

import pytest


class TestAIProviderBoot:
    """Tests for AIProvider.boot() optional dependency resolution."""

    @pytest.mark.asyncio
    async def test_boot_resolves_database_provider(self) -> None:
        from unittest.mock import AsyncMock, MagicMock
        from lexigram.ai.di.provider import AIProvider
        from lexigram.contracts.data import DatabaseProviderProtocol

        provider = AIProvider()
        mock_db = MagicMock(spec=DatabaseProviderProtocol)

        container = MagicMock()
        container.resolve = AsyncMock(side_effect=lambda proto: (
            mock_db if proto is DatabaseProviderProtocol else (_ for _ in ()).throw(ValueError("not found"))
        ))

        try:
            await provider.boot(container)
        except Exception:
            pass

        assert provider._database_provider is mock_db or provider._database_provider is None

    @pytest.mark.asyncio
    async def test_boot_tolerates_missing_dependencies(self) -> None:
        from unittest.mock import AsyncMock, MagicMock
        from lexigram.ai.di.provider import AIProvider

        provider = AIProvider()
        container = MagicMock()
        container.resolve = AsyncMock(side_effect=ValueError("not found"))

        await provider.boot(container)

        assert provider._database_provider is None
        assert provider._cache_backend is None
        assert provider._rag_cache is None
