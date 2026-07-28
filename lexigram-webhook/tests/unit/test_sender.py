"""Tests for WebhookSender."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import Response

from lexigram.contracts.webhook.types import DeliveryStatus, WebhookEvent, WebhookSubscription
from lexigram.webhook.config import WebhookConfig
from lexigram.webhook.delivery.sender import WebhookSender


@pytest.fixture
def sender() -> WebhookSender:
    return WebhookSender(config=WebhookConfig())


@pytest.fixture
def event() -> WebhookEvent:
    return WebhookEvent(
        event_id="e1",
        event_type="user.created",
        payload={"id": "u1"},
    )


@pytest.fixture
def subscription() -> WebhookSubscription:
    return WebhookSubscription(
        subscription_id="sub1",
        url="https://example.com/webhook",
        secret="test-secret",
    )


@pytest.mark.asyncio
async def test_webhook_sender_success(
    sender: WebhookSender,
    event: WebhookEvent,
    subscription: WebhookSubscription,
) -> None:
    """Test successful delivery."""
    mock_response = Response(200, content=b"OK")
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        attempt = await sender.send(event, subscription)
        
        assert attempt.status == DeliveryStatus.DELIVERED
        assert attempt.status_code == 200
        assert attempt.error_message is None
        
        mock_post.assert_called_once()
        # Verify headers were sent
        _, kwargs = mock_post.call_args
        headers = kwargs["headers"]
        assert "X-Webhook-Signature" in headers
        assert headers["X-Webhook-Event-Type"] == "user.created"
        assert headers["X-Webhook-Event-ID"] == "e1"


@pytest.mark.asyncio
async def test_webhook_sender_http_error(
    sender: WebhookSender,
    event: WebhookEvent,
    subscription: WebhookSubscription,
) -> None:
    """Test delivery resulting in HTTP error."""
    mock_response = Response(400, content=b"Bad Request")
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        attempt = await sender.send(event, subscription)
        
        assert attempt.status == DeliveryStatus.FAILED
        assert attempt.status_code == 400
        assert "HTTP 400: Bad Request" in attempt.error_message


@pytest.mark.asyncio
async def test_webhook_sender_connection_error(
    sender: WebhookSender,
    event: WebhookEvent,
    subscription: WebhookSubscription,
) -> None:
    """Test delivery resulting in connection exception."""
    
    with patch("httpx.AsyncClient.post", side_effect=Exception("Connection failed")):
        attempt = await sender.send(event, subscription)
        
        assert attempt.status == DeliveryStatus.FAILED
        assert attempt.status_code is None
        assert "Connection failed" in attempt.error_message
