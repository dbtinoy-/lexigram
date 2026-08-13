"""Tests for webhook domain events."""

from __future__ import annotations

from lexigram.webhook.events import (
    WebhookDeliveredEvent,
    WebhookDeliveryFailedEvent,
    WebhookSubscriptionCreatedEvent,
)


def test_webhook_subscription_created_event() -> None:
    """Test WebhookSubscriptionCreatedEvent creation and attributes."""
    event = WebhookSubscriptionCreatedEvent(
        subscription_id="sub-123",
        url="https://example.com/webhook",
    )
    assert event.subscription_id == "sub-123"
    assert event.url == "https://example.com/webhook"


def test_webhook_delivered_event() -> None:
    """Test WebhookDeliveredEvent creation and attributes."""
    event = WebhookDeliveredEvent(
        attempt_id="att-123",
        subscription_id="sub-123",
        event_type="user.created",
    )
    assert event.attempt_id == "att-123"
    assert event.subscription_id == "sub-123"
    assert event.event_type == "user.created"


def test_webhook_delivery_failed_event() -> None:
    """Test WebhookDeliveryFailedEvent creation and attributes."""
    event = WebhookDeliveryFailedEvent(
        attempt_id="att-123",
        subscription_id="sub-123",
        event_type="user.created",
        error="Connection refused",
        attempt_number=2,
    )
    assert event.attempt_id == "att-123"
    assert event.subscription_id == "sub-123"
    assert event.event_type == "user.created"
    assert event.error == "Connection refused"
    assert event.attempt_number == 2
