"""Tests for DeadLetterManager."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.webhook.protocols import WebhookDeliveryStoreProtocol
from lexigram.contracts.webhook.types import DeliveryAttempt, DeliveryStatus
from lexigram.webhook.delivery.dead_letter import DeadLetterManager


@pytest.mark.asyncio
async def test_dead_letter_manager_list() -> None:
    """Test listing dead-lettered attempts."""
    mock_store = MagicMock(spec=WebhookDeliveryStoreProtocol)
    mock_store.get_dead_letters = AsyncMock(return_value=[])
    
    manager = DeadLetterManager(delivery_store=mock_store)
    
    await manager.list(subscription_id="sub-1", limit=10, offset=5)
    
    mock_store.get_dead_letters.assert_called_once_with(
        subscription_id="sub-1",
        limit=10,
        offset=5,
    )


@pytest.mark.asyncio
async def test_dead_letter_manager_count() -> None:
    """Test counting dead-lettered attempts."""
    attempts = [
        DeliveryAttempt(
            attempt_id="att-1",
            subscription_id="sub-1",
            event_id="e1",
            event_type="test",
            status=DeliveryStatus.DEAD_LETTER,
        )
    ]
    mock_store = MagicMock(spec=WebhookDeliveryStoreProtocol)
    mock_store.get_dead_letters = AsyncMock(return_value=attempts)
    
    manager = DeadLetterManager(delivery_store=mock_store)
    
    count = await manager.count(subscription_id="sub-1")
    
    assert count == 1
    mock_store.get_dead_letters.assert_called_once_with(
        subscription_id="sub-1",
        limit=10000,
    )