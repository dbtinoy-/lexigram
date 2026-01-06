"""Tests for WebhookAdminContributor."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.webhook.protocols import (
    WebhookDeliveryStoreProtocol,
    WebhookSubscriptionStoreProtocol,
)
from lexigram.contracts.webhook.types import DeliveryAttempt, DeliveryStatus, WebhookSubscription
from lexigram.webhook.admin.contributor import WebhookAdminContributor
from lexigram.webhook.config import WebhookConfig


@pytest.fixture
def mock_subscription_store() -> MagicMock:
    return MagicMock(spec=WebhookSubscriptionStoreProtocol)


@pytest.fixture
def mock_delivery_store() -> MagicMock:
    return MagicMock(spec=WebhookDeliveryStoreProtocol)


class MockContainer:
    """Mock DI container for admin resolution."""

    def __init__(self, services: dict[Any, Any]) -> None:
        self.services = services

    async def resolve(self, protocol: Any) -> Any:
        if protocol in self.services:
            return self.services[protocol]
        raise Exception(f"Service not found: {protocol}")


@pytest.mark.asyncio
async def test_webhook_admin_contributor_metadata() -> None:
    """Test basic metadata of the contributor."""
    contributor = WebhookAdminContributor()
    assert contributor.name == "webhooks"
    assert contributor.display_name == "Webhooks"
    assert contributor.group == "integrations"
    assert contributor.icon == "webhook"


@pytest.mark.asyncio
async def test_webhook_admin_contributor_boot(
    mock_subscription_store: MagicMock,
    mock_delivery_store: MagicMock,
) -> None:
    """Test dependency resolution during boot."""
    config = WebhookConfig()
    container = MockContainer(
        {
            WebhookSubscriptionStoreProtocol: mock_subscription_store,
            WebhookDeliveryStoreProtocol: mock_delivery_store,
            WebhookConfig: config,
        }
    )

    contributor = WebhookAdminContributor()
    await contributor.on_admin_boot(container)

    assert contributor._subscription_store == mock_subscription_store
    assert contributor._delivery_store == mock_delivery_store
    assert contributor._config == config


@pytest.mark.asyncio
async def test_webhook_admin_contributor_boot_failure() -> None:
    """Test boot handles resolution failure gracefully."""
    container = MockContainer({})  # Empty container causes failure

    contributor = WebhookAdminContributor()
    # Should not raise exception
    await contributor.on_admin_boot(container)

    assert contributor._subscription_store is None


@pytest.mark.asyncio
async def test_webhook_admin_contributor_nav_items() -> None:
    """Test navigation items generation."""
    contributor = WebhookAdminContributor()
    items = contributor.get_navigation_items()

    assert len(items) == 1
    root = items[0]
    assert root.label == "Webhooks"
    assert root.icon == "webhook"
    assert len(root.children) == 3
    assert root.children[0].label == "Subscriptions"
    assert root.children[1].label == "Deliveries"
    assert root.children[2].label == "Dead Letter"

    pages = contributor.get_management_pages()
    assert len(pages) == 3
    assert pages[0].name == "webhooks_subscriptions"
    assert pages[1].name == "webhooks_deliveries"
    assert pages[2].name == "webhooks_dead_letters"


@pytest.mark.asyncio
async def test_webhook_admin_contributor_health(
    mock_subscription_store: MagicMock,
    mock_delivery_store: MagicMock,
) -> None:
    """Test health metrics calculation."""
    # Setup mocks
    mock_subscription_store.list = AsyncMock(
        return_value=[
            WebhookSubscription(
                subscription_id="sub1", url="http://test1", secret="s1", active=True
            ),
            WebhookSubscription(
                subscription_id="sub2", url="http://test2", secret="s2", active=False
            ),
        ]
    )
    mock_delivery_store.get_dead_letters = AsyncMock(
        return_value=[
            DeliveryAttempt(
                attempt_id="att1",
                subscription_id="sub1",
                event_id="e1",
                event_type="test",
                status=DeliveryStatus.DEAD_LETTER,
            )
        ]
    )

    contributor = WebhookAdminContributor()
    contributor._subscription_store = mock_subscription_store
    contributor._delivery_store = mock_delivery_store

    health = await contributor.endpoint_health()

    assert health["total_subscriptions"] == 2
    assert health["active_subscriptions"] == 1
    assert health["dead_letter_count"] == 1

    mock_subscription_store.list.assert_called_once_with(active_only=False, limit=10000)
    mock_delivery_store.get_dead_letters.assert_called_once_with(limit=10000)
