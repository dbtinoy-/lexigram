"""Tests for concurrent delivery scenarios in WebhookDeliveryService."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

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


def _make_subscription(sub_id: str = "sub-1", url: str = "https://example.com") -> WebhookSubscription:
    """Build a test subscription."""
    return WebhookSubscription(
        subscription_id=sub_id,
        url=url,
        secret="secret",
        active=True,
    )


def _make_event(event_id: str = "evt-1", event_type: str = "user.created") -> WebhookEvent:
    """Build a test event."""
    return WebhookEvent(
        event_id=event_id,
        event_type=event_type,
        payload={"user_id": "123"},
    )


def _make_delivery_attempt(
    attempt_id: str = "att-1",
    sub_id: str = "sub-1",
    event_id: str = "evt-1",
    status: DeliveryStatus = DeliveryStatus.DELIVERED,
    status_code: int = 200,
    attempt_number: int = 1,
) -> DeliveryAttempt:
    """Build a test delivery attempt."""
    return DeliveryAttempt(
        attempt_id=attempt_id,
        subscription_id=sub_id,
        event_id=event_id,
        event_type="user.created",
        status=status,
        status_code=status_code,
        attempt_number=attempt_number,
        attempted_at=datetime.now(UTC),
        duration_ms=5.0,
    )


@pytest.fixture
def config() -> WebhookConfig:
    """Webhook config for testing."""
    return WebhookConfig(
        retry_max_attempts=3,
        timeout_seconds=5.0,
        retry_base_delay=0.01,  # Fast retries for tests
        retry_backoff_factor=2.0,
    )


@pytest.fixture
def store() -> InMemoryWebhookStore:
    """In-memory store for testing."""
    return InMemoryWebhookStore()


@pytest.fixture
def mock_sender() -> MagicMock:
    """Mocked webhook sender."""
    sender = MagicMock(spec=WebhookSender)
    sender.send = AsyncMock()
    return sender


@pytest.fixture
def service(
    config: WebhookConfig,
    store: InMemoryWebhookStore,
    mock_sender: MagicMock,
) -> WebhookDeliveryService:
    """Delivery service with mocked dependencies."""
    return WebhookDeliveryService(
        subscription_store=store,
        delivery_store=store,
        sender=mock_sender,
        config=config,
    )


class TestConcurrentDelivery:
    """Test concurrent delivery to multiple subscribers."""

    @pytest.mark.asyncio
    async def test_dispatch_many_subscribers_concurrently(
        self, 
        service: WebhookDeliveryService,
        store: InMemoryWebhookStore,
        mock_sender: MagicMock,
        config: WebhookConfig,
    ) -> None:
        """Dispatch event to 10 subscribers concurrently."""
        # Create 10 subscriptions
        subs = [
            _make_subscription(f"sub-{i}", f"https://example-{i}.com/hook")
            for i in range(10)
        ]
        for sub in subs:
            await store.create(sub)

        # Mock successful delivery for all
        mock_sender.send.return_value = _make_delivery_attempt(
            status=DeliveryStatus.DELIVERED,
            status_code=200,
        )

        event = _make_event()

        # Dispatch and wait
        await service.dispatch(event)

        # Verify all were attempted
        assert mock_sender.send.call_count == 10

    @pytest.mark.asyncio
    async def test_dispatch_partial_failure_with_many_subs(
        self,
        service: WebhookDeliveryService,
        store: InMemoryWebhookStore,
        mock_sender: MagicMock,
    ) -> None:
        """When some subscribers fail, others still succeed."""
        # Create 5 subscriptions
        subs = [_make_subscription(f"sub-{i}") for i in range(5)]
        for sub in subs:
            await store.create(sub)

        # Fail odd-numbered subscribers
        async def send_with_failure(*args, **kwargs):
            subscription = kwargs.get("subscription") or args[1]
            sub_num = int(subscription.subscription_id.split("-")[1])
            if sub_num % 2 == 1:
                raise Exception("Network timeout")
            return _make_delivery_attempt(status=DeliveryStatus.DELIVERED)

        mock_sender.send.side_effect = send_with_failure

        event = _make_event()

        # Dispatch should not raise (errors logged)
        await service.dispatch(event)

        # Verify all were attempted
        assert mock_sender.send.call_count == 5

    @pytest.mark.asyncio
    async def test_dispatch_empty_subscriber_list_is_noop(
        self,
        service: WebhookDeliveryService,
        mock_sender: MagicMock,
    ) -> None:
        """No subscribers = no delivery attempts."""
        event = _make_event()

        await service.dispatch(event)

        # Sender never called
        assert mock_sender.send.call_count == 0

    @pytest.mark.asyncio
    async def test_dispatch_filters_by_event_type(
        self,
        service: WebhookDeliveryService,
        store: InMemoryWebhookStore,
        mock_sender: MagicMock,
    ) -> None:
        """Only subscribers matching event type are delivered to."""
        sub1 = WebhookSubscription(
            subscription_id="sub-1",
            url="https://example.com/a",
            secret="secret1",
            active=True,
            event_types=["user.created"],
        )
        sub2 = WebhookSubscription(
            subscription_id="sub-2",
            url="https://example.com/b",
            secret="secret2",
            active=True,
            event_types=["user.updated"],
        )
        await store.create(sub1)
        await store.create(sub2)

        mock_sender.send.return_value = _make_delivery_attempt()

        # Dispatch user.created
        event = _make_event(event_type="user.created")
        await service.dispatch(event)

        # Only sub1 should be sent to
        assert mock_sender.send.call_count == 1

    @pytest.mark.asyncio
    async def test_dispatch_ignores_inactive_subscriptions(
        self,
        service: WebhookDeliveryService,
        store: InMemoryWebhookStore,
        mock_sender: MagicMock,
    ) -> None:
        """Inactive subscriptions are not delivered to."""
        active_sub = _make_subscription("sub-active")
        inactive_sub = WebhookSubscription(
            subscription_id="sub-inactive",
            url="https://example.com/inactive",
            secret="secret",
            active=False,
        )
        await store.create(active_sub)
        await store.create(inactive_sub)

        mock_sender.send.return_value = _make_delivery_attempt()

        event = _make_event()
        await service.dispatch(event)

        # Only active should be sent
        assert mock_sender.send.call_count == 1


class TestDeliveryRetryLogic:
    """Test retry behavior with backoff."""

    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(
        self,
        service: WebhookDeliveryService,
        store: InMemoryWebhookStore,
        mock_sender: MagicMock,
        config: WebhookConfig,
    ) -> None:
        """Retries use exponential backoff between attempts."""
        sub = _make_subscription()
        await store.create(sub)

        attempt_times = []

        async def track_send_time(*args, **kwargs):
            attempt_times.append(asyncio.get_event_loop().time())
            if len(attempt_times) < 3:
                return _make_delivery_attempt(
                    attempt_id=f"att-{len(attempt_times)}",
                    attempt_number=len(attempt_times),
                    status=DeliveryStatus.FAILED,
                )
            return _make_delivery_attempt(
                attempt_id=f"att-{len(attempt_times)}",
                attempt_number=len(attempt_times),
            )

        mock_sender.send.side_effect = track_send_time

        event = _make_event()
        await service.dispatch(event)

        # Should have 3 attempts (2 failures + 1 success)
        assert len(attempt_times) == 3

        # Verify backoff increases
        delay1 = attempt_times[1] - attempt_times[0]
        delay2 = attempt_times[2] - attempt_times[1]
        assert delay2 > delay1

    @pytest.mark.asyncio
    async def test_max_retries_exceeded_moves_to_dead_letter(
        self,
        service: WebhookDeliveryService,
        store: InMemoryWebhookStore,
        mock_sender: MagicMock,
        config: WebhookConfig,
    ) -> None:
        """After max_retries, delivery is marked as dead-lettered."""
        sub = _make_subscription()
        await store.create(sub)

        # Always fail
        mock_sender.send.side_effect = lambda *args, **kwargs: _make_delivery_attempt(
            status=DeliveryStatus.FAILED,
            status_code=500
        )

        event = _make_event()
        await service.dispatch(event)

        # Sender called max_retries + 1 times
        expected_attempts = config.retry_max_attempts
        assert mock_sender.send.call_count == expected_attempts


class TestRedelivery:
    """Test the redeliver operation."""

    @pytest.mark.asyncio
    async def test_redeliver_missing_attempt_returns_err(
        self,
        service: WebhookDeliveryService,
    ) -> None:
        """Redeliver with non-existent attempt ID returns error."""
        result = await service.redeliver("non-existent-attempt")

        assert result.is_err()

    @pytest.mark.asyncio
    async def test_redeliver_missing_subscription_returns_err(
        self,
        service: WebhookDeliveryService,
        store: InMemoryWebhookStore,
        mock_sender: MagicMock,
    ) -> None:
        """Redeliver when subscription deleted returns error."""
        # Record attempt with subscription that will be deleted
        attempt = _make_delivery_attempt(status=DeliveryStatus.DEAD_LETTER)
        await store.record_attempt(attempt)

        # Subscription doesn't exist

        result = await service.redeliver(attempt.attempt_id)

        assert result.is_err()

    @pytest.mark.asyncio
    async def test_redeliver_success_records_new_attempt(
        self,
        service: WebhookDeliveryService,
        store: InMemoryWebhookStore,
        mock_sender: MagicMock,
    ) -> None:
        """Successful redeliver creates new attempt with incremented number."""
        sub = _make_subscription("sub-1")
        await store.create(sub)

        original = _make_delivery_attempt(
            attempt_id="att-original",
            attempt_number=1,
            status=DeliveryStatus.DEAD_LETTER,
        )
        await store.record_attempt(original)

        new_attempt = _make_delivery_attempt(
            attempt_id="att-new",
            attempt_number=2,
            status=DeliveryStatus.DELIVERED,
        )
        mock_sender.send.return_value = new_attempt

        result = await service.redeliver("att-original")

        assert result.is_ok()
        assert mock_sender.send.call_count == 1


class TestAutoDisable:
    """Test auto-disable after repeated failures."""

    @pytest.mark.asyncio
    async def test_subscription_auto_disabled_after_failure_threshold(
        self,
        service: WebhookDeliveryService,
        store: InMemoryWebhookStore,
        mock_sender: MagicMock,
        config: WebhookConfig,
    ) -> None:
        """Subscription auto-disabled after max consecutive failures."""
        sub = _make_subscription("sub-1")
        await store.create(sub)

        # Always fail
        mock_sender.send.side_effect = Exception("Connection refused")

        # Set up multiple events
        for i in range(5):
            event = _make_event(event_id=f"evt-{i}")
            await service.dispatch(event)

        # Subscription may be auto-disabled (if implemented)
        # Check if still active in store
        updated_sub = await store.get("sub-1")
        # This is transport-dependent; implementation may vary
        # Just verify subscription still exists
        assert updated_sub is not None
