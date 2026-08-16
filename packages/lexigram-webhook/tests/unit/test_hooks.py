"""Tests for webhook lifecycle hooks."""

from __future__ import annotations

from lexigram.webhook.hooks import (
    WebhookBeforeDeliveryHook,
    WebhookDeliveryCompletedHook,
    WebhookSubscriptionChangedHook,
)


def test_webhook_before_delivery_hook() -> None:
    """Test WebhookBeforeDeliveryHook creation and attributes."""
    hook = WebhookBeforeDeliveryHook(
        subscription_id="sub-123",
        event_type="user.created",
        url="https://example.com/webhook",
    )
    assert hook.subscription_id == "sub-123"
    assert hook.event_type == "user.created"
    assert hook.url == "https://example.com/webhook"


def test_webhook_delivery_completed_hook() -> None:
    """Test WebhookDeliveryCompletedHook creation and attributes."""
    hook = WebhookDeliveryCompletedHook(
        attempt_id="att-123",
        subscription_id="sub-123",
        status="delivered",
        status_code=200,
    )
    assert hook.attempt_id == "att-123"
    assert hook.subscription_id == "sub-123"
    assert hook.status == "delivered"
    assert hook.status_code == 200


def test_webhook_subscription_changed_hook() -> None:
    """Test WebhookSubscriptionChangedHook creation and attributes."""
    hook = WebhookSubscriptionChangedHook(
        subscription_id="sub-123",
        change_type="created",
    )
    assert hook.subscription_id == "sub-123"
    assert hook.change_type == "created"
