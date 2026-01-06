"""Tests for WebhookSender."""

from __future__ import annotations

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


@pytest.fixture
def config() -> WebhookConfig:
    return WebhookConfig()


@pytest.fixture
def sender(config: WebhookConfig) -> WebhookSender:
    return WebhookSender(config=config)


def _make_event(event_id: str = "evt-1") -> WebhookEvent:
    return WebhookEvent(
        event_id=event_id,
        event_type="user.created",
        payload={"user_id": "123"},
    )


def _make_subscription(
    sub_id: str = "sub-1",
    url: str = "https://example.com/hook",
) -> WebhookSubscription:
    return WebhookSubscription(
        subscription_id=sub_id,
        url=url,
        secret="test-secret",
        active=True,
    )


class TestWebhookSender:
    """Tests for WebhookSender."""

    @pytest.mark.asyncio
    async def test_send_returns_delivery_attempt(
        self, sender: WebhookSender
    ) -> None:
        """send() returns a DeliveryAttempt."""
        event = _make_event()
        subscription = _make_subscription()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = "OK"
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            attempt = await sender.send(event, subscription)
            assert attempt is not None
            assert attempt.attempt_id
            assert attempt.event_id == event.event_id
            assert attempt.subscription_id == subscription.subscription_id

    @pytest.mark.asyncio
    async def test_send_success_returns_delivered_status(
        self, sender: WebhookSender
    ) -> None:
        """send() returns DELIVERED status on 2xx response."""
        event = _make_event()
        subscription = _make_subscription()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = "OK"
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            attempt = await sender.send(event, subscription)
            assert attempt.status == DeliveryStatus.DELIVERED

    @pytest.mark.asyncio
    async def test_send_server_error_returns_failed_status(
        self, sender: WebhookSender
    ) -> None:
        """send() returns FAILED status on 5xx response."""
        event = _make_event()
        subscription = _make_subscription()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            attempt = await sender.send(event, subscription)
            assert attempt.status == DeliveryStatus.FAILED
            assert attempt.status_code == 500
            assert attempt.error_message is not None

    @pytest.mark.asyncio
    async def test_send_client_error_returns_failed_status(
        self, sender: WebhookSender
    ) -> None:
        """send() returns FAILED status on 4xx response."""
        event = _make_event()
        subscription = _make_subscription()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 400
            mock_response.text = "Bad Request"
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            attempt = await sender.send(event, subscription)
            assert attempt.status == DeliveryStatus.FAILED
            assert attempt.status_code == 400

    @pytest.mark.asyncio
    async def test_send_network_error_captured(
        self, sender: WebhookSender
    ) -> None:
        """send() captures network errors in error_message."""
        event = _make_event()
        subscription = _make_subscription()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=Exception("Connection refused")
            )

            attempt = await sender.send(event, subscription)
            assert attempt.status == DeliveryStatus.FAILED
            assert attempt.error_message is not None
            assert "Connection refused" in attempt.error_message

    @pytest.mark.asyncio
    async def test_send_includes_correct_headers(
        self, sender: WebhookSender
    ) -> None:
        """send() includes correct webhook headers."""
        event = _make_event()
        subscription = _make_subscription()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = "OK"
            
            post_mock = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = post_mock

            await sender.send(event, subscription)

            call_kwargs = post_mock.call_args.kwargs
            headers = call_kwargs.get("headers", {})
            assert "Content-Type" in headers
            assert headers["Content-Type"] == "application/json"
            assert "X-Webhook-Signature" in headers
            assert "X-Webhook-Event-Type" in headers
            assert "X-Webhook-Event-ID" in headers
            assert "X-Webhook-Timestamp" in headers

    @pytest.mark.asyncio
    async def test_send_records_attempt_number(
        self, sender: WebhookSender
    ) -> None:
        """send() records the attempt_number."""
        event = _make_event()
        subscription = _make_subscription()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = "OK"
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            attempt = await sender.send(event, subscription, attempt_number=3)
            assert attempt.attempt_number == 3

    @pytest.mark.asyncio
    async def test_send_records_duration_ms(
        self, sender: WebhookSender
    ) -> None:
        """send() records the duration in milliseconds."""
        event = _make_event()
        subscription = _make_subscription()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = "OK"
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            attempt = await sender.send(event, subscription)
            assert attempt.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_send_includes_event_type(
        self, sender: WebhookSender
    ) -> None:
        """send() includes the event_type in the attempt."""
        event = _make_event()
        subscription = _make_subscription()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = "OK"
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            attempt = await sender.send(event, subscription)
            assert attempt.event_type == "user.created"

    @pytest.mark.asyncio
    async def test_sender_accepts_custom_verifier(
        self, config: WebhookConfig
    ) -> None:
        """WebhookSender accepts custom verifier in constructor."""
        from lexigram.webhook.verification.hmac import HMACSignatureVerifier
        
        custom_verifier = HMACSignatureVerifier()
        sender = WebhookSender(config=config, verifier=custom_verifier)
        assert sender is not None