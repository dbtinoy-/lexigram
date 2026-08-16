"""Tests for EventBusWebhookBridge."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.webhook.protocols import WebhookDeliveryServiceProtocol
from lexigram.contracts.webhook.types import WebhookEvent
from lexigram.webhook.bridge.event_bus import EventBusWebhookBridge


@pytest.mark.asyncio
async def test_event_bus_webhook_bridge_forward() -> None:
    """Test forwarding an event through the bridge."""
    mock_delivery_service = MagicMock(spec=WebhookDeliveryServiceProtocol)
    mock_delivery_service.dispatch = AsyncMock()
    
    bridge = EventBusWebhookBridge(delivery_service=mock_delivery_service)
    
    event = WebhookEvent(
        event_id="e1",
        event_type="user.created",
        payload={"id": "u1"},
    )
    
    await bridge.forward(event)
    
    mock_delivery_service.dispatch.assert_called_once_with(event)
