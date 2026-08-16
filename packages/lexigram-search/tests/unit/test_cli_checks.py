"""Tests for CLI health checks module."""
from __future__ import annotations

from unittest.mock import MagicMock, AsyncMock

import pytest

from lexigram.search.cli.checks import check_search_backend


class TestCheckSearchBackend:
    """Tests for check_search_backend."""

    @pytest.mark.asyncio
    async def test_check_search_backend_returns_ok(self) -> None:
        """Verify health check returns expected dict."""
        mock_container = MagicMock()
        mock_container.resolve = AsyncMock()

        result = await check_search_backend(mock_container)

        assert result == {
            "status": "ok",
            "message": "Search backend health check not yet implemented",
        }

    @pytest.mark.asyncio
    async def test_check_search_backend_with_any_container(self) -> None:
        """Verify function works with any container-like object."""
        class FakeContainer:
            async def resolve(self, protocol):
                return object()

        container = FakeContainer()
        result = await check_search_backend(container)

        assert result["status"] == "ok"
