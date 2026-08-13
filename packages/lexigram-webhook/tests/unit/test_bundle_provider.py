"""Tests for WebhookBundleProvider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.core.di import ContainerRegistrarProtocol, ContainerResolverProtocol
from lexigram.webhook.config import WebhookConfig
from lexigram.webhook.di.bundle_provider import WebhookBundleProvider


@pytest.mark.asyncio
async def test_webhook_bundle_provider_init() -> None:
    """Test initialization with and without admin."""
    # With admin (default)
    provider = WebhookBundleProvider()
    assert len(provider._sub_providers) == 4
    
    # Without admin
    config = WebhookConfig()
    config.enable_admin = False
    provider = WebhookBundleProvider(config=config)
    assert len(provider._sub_providers) == 3


@pytest.mark.asyncio
async def test_webhook_bundle_provider_lifecycle() -> None:
    """Test register, boot, and shutdown delegation."""
    provider = WebhookBundleProvider()
    
    # Mock sub-providers
    for sub in provider._sub_providers:
        sub.register = AsyncMock()
        sub.boot = AsyncMock()
        sub.shutdown = AsyncMock()
        
    container_reg = MagicMock(spec=ContainerRegistrarProtocol)
    container_res = MagicMock(spec=ContainerResolverProtocol)
    
    await provider.register(container_reg)
    for sub in provider._sub_providers:
        sub.register.assert_called_once_with(container_reg)
        
    await provider.boot(container_res)
    for sub in provider._sub_providers:
        sub.boot.assert_called_once_with(container_res)
        
    await provider.shutdown()
    for sub in provider._sub_providers:
        sub.shutdown.assert_called_once()
