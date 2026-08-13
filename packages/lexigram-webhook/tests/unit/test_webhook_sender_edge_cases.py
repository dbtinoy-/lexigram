"""Additional tests for WebhookSender edge cases."""

from __future__ import annotations

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


class TestWebhookSenderEdgeCases:
    """Additional edge case tests for WebhookSender."""

    @pytest.mark.asyncio
    async def test_send_records_subscription_id(
        self, sender: WebhookSender
    ) -> None:
        """send() includes subscription_id in attempt."""
        event = _make_event()
        subscription = _make_subscription(sub_id="custom-sub-id")

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = "OK"
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            attempt = await sender.send(event, subscription)
            assert attempt.subscription_id == "custom-sub-id"

    @pytest.mark.asyncio
    async def test_send_includes_error_for_4xx(
        self, sender: WebhookSender
    ) -> None:
        """send() includes error message for 4xx responses."""
        event = _make_event()
        subscription = _make_subscription()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 404
            mock_response.text = "Not Found"
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            attempt = await sender.send(event, subscription)
            assert attempt.error_message is not None
            assert "404" in attempt.error_message

    @pytest.mark.asyncio
    async def test_send_includes_error_for_5xx(
        self, sender: WebhookSender
    ) -> None:
        """send() includes error message for 5xx responses."""
        event = _make_event()
        subscription = _make_subscription()

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 503
            mock_response.text = "Service Unavailable"
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            attempt = await sender.send(event, subscription)
            assert attempt.error_message is not None

    @pytest.mark.asyncio
    async def test_sends_error_with_long_response_body(
        self, sender: WebhookSender
    ) -> None:
        """send() handles long error response body."""
        event = _make_event()
        subscription = _make_subscription()

        long_text = "x" * 500

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_response.text = long_text
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            attempt = await sender.send(event, subscription)
            # Error should include some of the response text
            assert attempt.error_message is not None

    @pytest.mark.asyncio
    async def test_sender_uses_config_timeout(
        self, sender: WebhookSender
    ) -> None:
        """sender uses config delivery_timeout_seconds."""
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
            assert call_kwargs.get("timeout") == sender._config.delivery_timeout_seconds

    @pytest.mark.asyncio
    async def test_sender_uses_config_header_names(
        self, config: WebhookSender
    ) -> None:
        """sender uses config header names."""
        cfg = WebhookConfig(
            signature_header="X-Custom-Sig",
            event_type_header="X-Custom-Type",
            event_id_header="X-Custom-ID",
            timestamp_header="X-Custom-Time",
        )
        sender = WebhookSender(config=cfg)
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
            assert "X-Custom-Sig" in headers
            assert "X-Custom-Type" in headers
            assert "X-Custom-ID" in headers
            assert "X-Custom-Time" in headers


class TestWebhookSenderPayloadHandling:
    """Tests for payload handling in WebhookSender."""

    @pytest.mark.asyncio
    async def test_send_serializes_json_payload(
        self, sender: WebhookSender
    ) -> None:
        """send() serializes payload as JSON."""
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
            content = call_kwargs.get("content", b"")
            assert content.startswith(b"{")

    @pytest.mark.asyncio
    async def test_send_with_complex_payload(
        self, sender: WebhookSender
    ) -> None:
        """send() handles complex nested payloads."""
        event = WebhookEvent(
            event_id="evt-1",
            event_type="order.created",
            payload={
                "order_id": "123",
                "items": [
                    {"product_id": "prod-1", "quantity": 2},
                    {"product_id": "prod-2", "quantity": 1},
                ],
                "customer": {
                    "name": "John Doe",
                    "email": "john@example.com",
                },
            },
        )
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


class TestWebhookSenderErrorHandling:
    """Tests for error handling in WebhookSender."""

    @pytest.mark.asyncio
    async def test_send_timeout_error(
        self, sender: WebhookSender
    ) -> None:
        """send() handles timeout errors."""
        event = _make_event()
        subscription = _make_subscription()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=TimeoutError()
            )

            attempt = await sender.send(event, subscription)
            assert attempt.status == DeliveryStatus.FAILED
            assert attempt.error_message is not None

    @pytest.mark.asyncio
    async def test_send_connection_error(
        self, sender: WebhookSender
    ) -> None:
        """send() handles connection errors."""
        event = _make_event()
        subscription = _make_subscription()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=ConnectionError("Connection refused")
            )

            attempt = await sender.send(event, subscription)
            assert attempt.status == DeliveryStatus.FAILED


class TestWebhookSenderInit:
    """Tests for WebhookSender initialization."""

    def test_init_with_default_verifier(self, config: WebhookConfig) -> None:
        """WebhookSender init with default verifier."""
        sender = WebhookSender(config=config)
        assert sender._verifier is not None

    def test_init_with_custom_verifier(self, config: WebhookConfig) -> None:
        """WebhookSender init with custom verifier."""
        from lexigram.webhook.verification.hmac import HMACSignatureVerifier
        
        custom_verifier = HMACSignatureVerifier()
        sender = WebhookSender(config=config, verifier=custom_verifier)
        assert sender._verifier is custom_verifier