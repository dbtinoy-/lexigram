"""Advanced tests for FeedbackProvider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.ai.feedback.config import FeedbackConfig
from lexigram.ai.feedback.di.provider import FeedbackProvider
from lexigram.ai.feedback.services.collector import FeedbackCollector
from lexigram.contracts.ai.feedback import FeedbackProtocol
from lexigram.contracts.core.health import HealthStatus
from lexigram.contracts.core.provider import ProviderPriority


class TestFeedbackProviderAdvanced:
    """Advanced tests for FeedbackProvider."""

    def test_name(self) -> None:
        provider = FeedbackProvider()
        assert provider.name == "feedback"

    def test_priority(self) -> None:
        provider = FeedbackProvider()
        assert provider.priority == ProviderPriority.DOMAIN

    def test_from_config(self) -> None:
        config = FeedbackConfig(enabled=True)
        provider = FeedbackProvider.from_config(config)
        assert provider._config.enabled is True

    def test_from_config_with_dict(self) -> None:
        provider = FeedbackProvider(config={"enabled": True})
        assert provider._config.enabled is True

    @pytest.mark.asyncio
    async def test_register_disabled(self) -> None:
        provider = FeedbackProvider(config=FeedbackConfig(enabled=False))
        container = MagicMock()
        await provider.register(container)
        container.singleton.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_enabled(self) -> None:
        provider = FeedbackProvider(config=FeedbackConfig(enabled=True))
        container = MagicMock()
        await provider.register(container)
        assert container.singleton.call_count == 4

    @pytest.mark.asyncio
    async def test_boot_disabled(self) -> None:
        provider = FeedbackProvider(config=FeedbackConfig(enabled=False))
        container = MagicMock()
        await provider.boot(container)
        container.resolve_optional.assert_not_called()

    @pytest.mark.asyncio
    async def test_boot_no_db_provider(self) -> None:
        provider = FeedbackProvider(config=FeedbackConfig(enabled=True))
        container = MagicMock()
        container.resolve_optional = AsyncMock(return_value=None)
        container.resolve = MagicMock(return_value=FeedbackCollector())
        await provider.boot(container)
        assert container.resolve_optional.call_count == 1

    @pytest.mark.asyncio
    async def test_shutdown(self) -> None:
        provider = FeedbackProvider()
        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        provider = FeedbackProvider()
        result = await provider.health_check()
        assert result.status == HealthStatus.HEALTHY
        assert result.details == {"status": "operational"}
