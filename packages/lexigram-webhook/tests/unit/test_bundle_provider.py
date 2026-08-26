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
    # Zero-config construction defers composition to register() so the
    # orchestrator can inject the yaml section first.
    provider = WebhookBundleProvider()
    assert len(provider._sub_providers) == 0

    # With admin (explicit default config)
    provider = WebhookBundleProvider(config=WebhookConfig())
    assert len(provider._sub_providers) == 4

    # Without admin
    config = WebhookConfig()
    config.enable_admin = False
    provider = WebhookBundleProvider(config=config)
    assert len(provider._sub_providers) == 3


@pytest.mark.asyncio
async def test_webhook_bundle_provider_lifecycle() -> None:
    """Test register, boot, and shutdown delegation."""
    provider = WebhookBundleProvider(config=WebhookConfig())

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


@pytest.mark.asyncio
async def test_webhook_bundle_provider_late_config_composition() -> None:
    """Zero-config construction composes sub-providers at register() time."""
    provider = WebhookBundleProvider()
    assert provider.config is None

    container_reg = MagicMock(spec=ContainerRegistrarProtocol)
    await provider.register(container_reg)

    # Composition happened during register(); admin enabled by default config.
    assert len(provider._sub_providers) == 4
