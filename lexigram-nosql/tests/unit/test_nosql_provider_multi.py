"""Tests for NoSQLProvider multi-backend support."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from lexigram.nosql.config import NamedNoSQLConfig, NoSQLConfig
from lexigram.nosql.di.provider import NoSQLProvider


class TestNoSQLProviderMultiBackend:
    def _make_config(self) -> NoSQLConfig:
        return NoSQLConfig(
            backends=[
                NamedNoSQLConfig(name="primary", primary=True),
                NamedNoSQLConfig(name="analytics"),
            ]
        )

    @pytest.mark.asyncio
    async def test_register_multi_backend_named_bindings(self) -> None:
        """Named bindings registered for each backend."""
        cfg = self._make_config()
        provider = NoSQLProvider(config=cfg)
        container = MagicMock()
        container.singleton = MagicMock()

        with patch("lexigram.nosql.di.provider.MongoDBDocumentStore"):
            await provider.register(container)

        names = [c.kwargs.get("name") for c in container.singleton.call_args_list]
        assert "primary" in names
        assert "analytics" in names

    @pytest.mark.asyncio
    async def test_primary_gets_unnamed_binding(self) -> None:
        """Primary backend also receives the unnamed DocumentStoreProtocol binding."""
        cfg = self._make_config()
        provider = NoSQLProvider(config=cfg)
        container = MagicMock()
        container.singleton = MagicMock()

        with patch("lexigram.nosql.di.provider.MongoDBDocumentStore"):
            await provider.register(container)

        # At least one call should have name=None (unnamed binding)
        unnamed_calls = [c for c in container.singleton.call_args_list if c.kwargs.get("name") is None]
        assert len(unnamed_calls) >= 1

    @pytest.mark.asyncio
    async def test_boot_connects_all_stores_in_parallel(self) -> None:
        """boot() calls connect() on all stores via asyncio.gather."""
        cfg = self._make_config()
        provider = NoSQLProvider(config=cfg)
        container = MagicMock()
        container.singleton = MagicMock()

        mock_store_1 = AsyncMock()
        mock_store_2 = AsyncMock()

        with patch("lexigram.nosql.di.provider.MongoDBDocumentStore", side_effect=[mock_store_1, mock_store_2]):
            await provider.register(container)
            await provider.boot(container)

        mock_store_1.connect.assert_awaited_once()
        mock_store_2.connect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_shutdown_disconnects_in_reverse(self) -> None:
        """shutdown() disconnects stores in reverse registration order."""
        cfg = self._make_config()
        provider = NoSQLProvider(config=cfg)
        container = MagicMock()
        container.singleton = MagicMock()
        call_order: list[str] = []

        mock_store_1 = AsyncMock()
        mock_store_1.connect = AsyncMock()
        mock_store_1.disconnect = AsyncMock(side_effect=lambda: call_order.append("primary"))
        mock_store_2 = AsyncMock()
        mock_store_2.connect = AsyncMock()
        mock_store_2.disconnect = AsyncMock(side_effect=lambda: call_order.append("analytics"))

        with patch("lexigram.nosql.di.provider.MongoDBDocumentStore", side_effect=[mock_store_1, mock_store_2]):
            await provider.register(container)
            await provider.boot(container)
            await provider.shutdown()

        assert call_order == ["analytics", "primary"]  # reversed order

    @pytest.mark.asyncio
    async def test_boot_cleans_up_on_partial_failure(self) -> None:
        """boot() disconnects successful backends if one fails."""
        cfg = self._make_config()
        provider = NoSQLProvider(config=cfg)
        container = MagicMock()
        container.singleton = MagicMock()

        mock_store_1 = AsyncMock()
        mock_store_2 = AsyncMock()
        mock_store_2.connect = AsyncMock(side_effect=RuntimeError("connection refused"))

        with patch("lexigram.nosql.di.provider.MongoDBDocumentStore", side_effect=[mock_store_1, mock_store_2]):
            await provider.register(container)
            with pytest.raises(RuntimeError, match="connection refused"):
                await provider.boot(container)

        # First store connected but then was disconnected (cleanup)
        mock_store_1.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_single_backend_unchanged(self) -> None:
        """Single-backend path still works (no regression)."""
        cfg = NoSQLConfig()  # no backends
        provider = NoSQLProvider(config=cfg)
        container = MagicMock()
        container.singleton = MagicMock()

        with patch("lexigram.nosql.di.provider.MongoDBDocumentStore"):
            await provider.register(container)

        assert container.singleton.called
