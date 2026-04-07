"""Unit tests for DurableIdempotencyProvider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.app.exceptions import AppStartupError
from lexigram.contracts.core.idempotency import IdempotencyStoreProtocol
from lexigram.contracts.infra.cache import CacheBackendProtocol
from lexigram.resilience.idempotency.durable_provider import DurableIdempotencyProvider
from lexigram.resilience.idempotency.redis import RedisIdempotencyStore


class TestDurableIdempotencyProviderMetadata:
    def test_provider_name(self) -> None:
        """Provider name is 'durable_idempotency'."""
        provider = DurableIdempotencyProvider()
        assert provider.name == "durable_idempotency"

    def test_provider_depends_on_core_idempotency(self) -> None:
        """Provider declares dependency on 'idempotency' (core provider)."""
        provider = DurableIdempotencyProvider()
        assert "idempotency" in provider.dependencies

    def test_provider_is_infrastructure_priority(self) -> None:
        """Provider uses INFRASTRUCTURE priority."""
        from lexigram.contracts.core import ProviderPriority

        provider = DurableIdempotencyProvider()
        assert provider.priority == ProviderPriority.INFRASTRUCTURE


class TestDurableIdempotencyProviderRegister:
    @pytest.mark.asyncio
    async def test_register_binds_redis_store_as_idempotency_store(self) -> None:
        """register() calls container.singleton with RedisIdempotencyStore factory."""
        provider = DurableIdempotencyProvider()
        container = MagicMock()
        container.singleton = MagicMock()

        await provider.register(container)

        container.singleton.assert_called_once_with(
            IdempotencyStoreProtocol, factory=RedisIdempotencyStore
        )


class TestDurableIdempotencyProviderBoot:
    @pytest.mark.asyncio
    async def test_boot_succeeds_when_cache_backend_is_registered(self) -> None:
        """boot() completes without error when CacheBackendProtocol resolves successfully."""
        provider = DurableIdempotencyProvider()
        container = MagicMock()
        container.resolve = AsyncMock(return_value=MagicMock(spec=CacheBackendProtocol))

        await provider.boot(container)  # Should not raise

        container.resolve.assert_awaited_once_with(CacheBackendProtocol)

    @pytest.mark.asyncio
    async def test_boot_raises_startup_error_when_cache_backend_missing(self) -> None:
        """boot() raises AppStartupError when the container cannot resolve CacheBackendProtocol."""
        provider = DurableIdempotencyProvider()
        container = MagicMock()
        container.resolve = AsyncMock(side_effect=RuntimeError("not registered"))

        with pytest.raises(AppStartupError, match="CacheBackendProtocol"):
            await provider.boot(container)

    @pytest.mark.asyncio
    async def test_shutdown_is_a_no_op(self) -> None:
        """shutdown() completes without side effects."""
        provider = DurableIdempotencyProvider()
        await provider.shutdown()
