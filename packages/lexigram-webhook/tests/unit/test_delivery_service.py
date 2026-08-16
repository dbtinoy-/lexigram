"""Tests for WebhookDeliveryService."""

from __future__ import annotations
from enum import Enum

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from lexigram.contracts.webhook.types import (
    DeliveryAttempt,
    DeliveryStatus,
    WebhookEvent,
    WebhookSubscription,
)
from lexigram.webhook.config import WebhookConfig
from lexigram.webhook.delivery.sender import WebhookSender
from lexigram.webhook.delivery.service import WebhookDeliveryService
from lexigram.webhook.store.memory import InMemoryWebhookStore


def _make_subscription(sub_id: str = "sub-1") -> WebhookSubscription:
    return WebhookSubscription(
        subscription_id=sub_id,
        url="https://example.com/hook",
        secret="secret",
        active=True,
    )


def _delivered_attempt(sub_id: str = "sub-1", event_id: str = "evt-1") -> DeliveryAttempt:
    return DeliveryAttempt(
        attempt_id="att-ok",
        subscription_id=sub_id,
        event_id=event_id,
        event_type="user.created",
        status=DeliveryStatus.DELIVERED,
        status_code=200,
        attempt_number=1,
        attempted_at=datetime.now(UTC),
        duration_ms=10.0,
    )


def _failed_attempt(
    sub_id: str = "sub-1",
    event_id: str = "evt-1",
    attempt_number: int = 1,
) -> DeliveryAttempt:
    return DeliveryAttempt(
        attempt_id=f"att-fail-{attempt_number}",
        subscription_id=sub_id,
        event_id=event_id,
        event_type="user.created",
        status=DeliveryStatus.FAILED,
        status_code=500,
        attempt_number=attempt_number,
        attempted_at=datetime.now(UTC),
        error_message="Server error",
        duration_ms=50.0,
    )


@pytest.fixture
def fast_config() -> WebhookConfig:
    """Config with minimal retry delay for fast tests."""
    return WebhookConfig(
        retry_max_attempts=3,
        retry_base_delay=0.0,
        retry_max_delay=0.0,
        retry_backoff_factor=1.0,
    )


@pytest.fixture
def delivery_service(
    store: InMemoryWebhookStore,
    fast_config: WebhookConfig,
) -> WebhookDeliveryService:
    """DeliveryService with mock sender injected."""
    mock_sender = AsyncMock(spec=WebhookSender)
    mock_sender.send.return_value = _delivered_attempt()
    return WebhookDeliveryService(
        subscription_store=store,
        delivery_store=store,
        sender=mock_sender,
        config=fast_config,
    )


class TestWebhookDeliveryService:
    """Tests for WebhookDeliveryService."""

    @pytest.mark.asyncio
    async def test_dispatch_fan_out(
        self, store: InMemoryWebhookStore, fast_config: WebhookConfig
    ) -> None:
        """dispatch() delivers to all matching active subscriptions."""
        await store.create(_make_subscription("sub-1"))
        await store.create(_make_subscription("sub-2"))

        call_tracker: list[str] = []

        async def mock_send(
            event: WebhookEvent,
            subscription: WebhookSubscription,
            attempt_number: int = 1,
        ) -> DeliveryAttempt:
            call_tracker.append(subscription.subscription_id)
            return _delivered_attempt(sub_id=subscription.subscription_id)

        mock_sender = AsyncMock(spec=WebhookSender)
        mock_sender.send.side_effect = mock_send

        service = WebhookDeliveryService(
            subscription_store=store,
            delivery_store=store,
            sender=mock_sender,
            config=fast_config,
        )

        event = WebhookEvent(
            event_id="evt-1",
            event_type="user.created",
            payload={"user_id": "123"},
        )
        await service.dispatch(event)
        assert set(call_tracker) == {"sub-1", "sub-2"}

    @pytest.mark.asyncio
    async def test_dispatch_records_delivered_attempt(
        self, store: InMemoryWebhookStore, fast_config: WebhookConfig
    ) -> None:
        """dispatch() records a DELIVERED attempt on success."""
        await store.create(_make_subscription("sub-1"))

        mock_sender = AsyncMock(spec=WebhookSender)
        mock_sender.send.return_value = _delivered_attempt()

        service = WebhookDeliveryService(
            subscription_store=store,
            delivery_store=store,
            sender=mock_sender,
            config=fast_config,
        )
        event = WebhookEvent(
            event_id="evt-1",
            event_type="user.created",
            payload={},
        )
        await service.dispatch(event)

        attempts = await store.get_attempts(status=DeliveryStatus.DELIVERED)
        assert len(attempts) == 1

    @pytest.mark.asyncio
    async def test_dispatch_dead_letters_after_max_retries(
        self, store: InMemoryWebhookStore, fast_config: WebhookConfig
    ) -> None:
        """dispatch() dead-letters when all retries exhausted."""
        await store.create(_make_subscription("sub-1"))

        mock_sender = AsyncMock(spec=WebhookSender)
        mock_sender.send.side_effect = [
            _failed_attempt(attempt_number=i)
            for i in range(1, fast_config.retry_max_attempts + 1)
        ]

        service = WebhookDeliveryService(
            subscription_store=store,
            delivery_store=store,
            sender=mock_sender,
            config=fast_config,
        )
        event = WebhookEvent(
            event_id="evt-1",
            event_type="user.created",
            payload={},
        )
        await service.dispatch(event)

        dead = await store.get_dead_letters()
        assert len(dead) == 1

    @pytest.mark.asyncio
    async def test_dispatch_no_subscribers_is_noop(
        self, store: InMemoryWebhookStore, fast_config: WebhookConfig
    ) -> None:
        """dispatch() does nothing when there are no matching subscriptions."""
        mock_sender = AsyncMock(spec=WebhookSender)
        service = WebhookDeliveryService(
            subscription_store=store,
            delivery_store=store,
            sender=mock_sender,
            config=fast_config,
        )
        event = WebhookEvent(
            event_id="evt-1",
            event_type="order.placed",
            payload={},
        )
        await service.dispatch(event)
        mock_sender.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_redeliver_missing_attempt_returns_err(
        self, store: InMemoryWebhookStore, fast_config: WebhookConfig
    ) -> None:
        """redeliver() returns Err when attempt_id is not found."""
        mock_sender = AsyncMock(spec=WebhookSender)
        service = WebhookDeliveryService(
            subscription_store=store,
            delivery_store=store,
            sender=mock_sender,
            config=fast_config,
        )
        result = await service.redeliver("nonexistent-attempt")
        assert result.is_err()

    @pytest.mark.asyncio
    async def test_auto_disable_after_threshold(
        self, store: InMemoryWebhookStore
    ) -> None:
        """_check_auto_disable() deactivates subscription when threshold exceeded."""
        cfg = WebhookConfig(
            retry_max_attempts=1,
            retry_base_delay=0.0,
            retry_max_delay=0.0,
            disable_after_consecutive_failures=1,
            failure_window_hours=24,
        )
        sub = _make_subscription("sub-1")
        await store.create(sub)

        mock_sender = AsyncMock(spec=WebhookSender)
        mock_sender.send.return_value = _failed_attempt()

        service = WebhookDeliveryService(
            subscription_store=store,
            delivery_store=store,
            sender=mock_sender,
            config=cfg,
        )
        event = WebhookEvent(
            event_id="evt-1",
            event_type="user.created",
            payload={},
        )
        await service.dispatch(event)

        updated_sub = await store.get("sub-1")
        assert updated_sub is not None
        assert updated_sub.active is False

    @pytest.mark.asyncio
    async def test_redeliver_success(
        self, store: InMemoryWebhookStore, fast_config: WebhookConfig
    ) -> None:
        """redeliver() successfully sends a new attempt."""
        sub = _make_subscription("sub-1")
        await store.create(sub)
        
        # Manually record a failed attempt to redeliver
        failed_att = _failed_attempt()
        await store.record_attempt(failed_att)
        
        mock_sender = AsyncMock(spec=WebhookSender)
        mock_sender.send.return_value = _delivered_attempt(event_id=failed_att.event_id)
        
        service = WebhookDeliveryService(
            subscription_store=store,
            delivery_store=store,
            sender=mock_sender,
            config=fast_config,
        )
        
        result = await service.redeliver(failed_att.attempt_id)
        assert result.is_ok()
        
        # Verify new attempt was recorded
        attempts = await store.get_attempts()
        assert len(attempts) == 2  # Original + new one
        assert any(a.status == DeliveryStatus.DELIVERED for a in attempts)

    @pytest.mark.asyncio
    async def test_redeliver_missing_subscription(
        self, store: InMemoryWebhookStore, fast_config: WebhookConfig
    ) -> None:
        """redeliver() returns Err when subscription is missing."""
        # Record attempt for a subscription that doesn't exist in store
        failed_att = _failed_attempt(sub_id="ghost-sub")
        await store.record_attempt(failed_att)
        
        service = WebhookDeliveryService(
            subscription_store=store,
            delivery_store=store,
            sender=AsyncMock(spec=WebhookSender),
            config=fast_config,
        )
        
        result = await service.redeliver(failed_att.attempt_id)
        assert result.is_err()
        assert "Subscription not found" in str(result.unwrap_err())
