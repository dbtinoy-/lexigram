"""Unit tests for InboxProvider health-check delegation."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.contracts.notification.inbox import InboxStoreProtocol
from lexigram.notification.di.inbox_provider import InboxProvider
from lexigram.notification.inbox.service import InboxService


class TestInboxProviderHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_degraded_before_boot(self) -> None:
        provider = InboxProvider()

        result = await provider.health_check()

        assert result.component == "inbox"
        assert result.status == HealthStatus.DEGRADED
        assert result.message == "inbox store not initialized"

    @pytest.mark.asyncio
    async def test_health_check_delegates_to_store_after_boot(self) -> None:
        provider = InboxProvider()
        store = MagicMock(spec=InboxStoreProtocol)
        store_health = HealthCheckResult(
            component="inbox_store",
            status=HealthStatus.HEALTHY,
            message="store healthy",
            details={"backend": "memory"},
            duration_ms=12.0,
        )
        store.health_check = AsyncMock(return_value=store_health)

        service = InboxService(store=store)

        async def resolve(dep: object) -> object:
            if dep is InboxService:
                return service
            if dep is InboxStoreProtocol:
                return store
            raise AssertionError(f"Unexpected resolve target: {dep!r}")

        container = MagicMock()
        container.resolve = AsyncMock(side_effect=resolve)

        await provider.boot(container)

        result = await provider.health_check(timeout=2.0)

        assert result.component == "inbox"
        assert result.status == store_health.status
        assert result.message == store_health.message
        assert result.details == store_health.details
        assert result.error is store_health.error
        assert result.duration_ms == store_health.duration_ms
        store.health_check.assert_awaited_once_with(timeout=2.0)
