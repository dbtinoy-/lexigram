"""Tests — real composition root, no mocks.

Every test boots a real Application with the actual DI container.
Services are tested through their public API, not by mocking internals.
"""

from __future__ import annotations

import httpx
import pytest

from lexigram.serialization import dumps
from lexigram.webhook.verification.hmac import HMACSignatureVerifier


class TestWebhookReceiving:
    """Test webhook receiving endpoints."""

    @pytest.mark.asyncio
    async def test_receive_webhook(self, client: httpx.AsyncClient) -> None:
        """POST /api/webhook/receive processes a webhook."""
        resp = await client.post(
            "/api/webhook/receive",
            json={"event_type": "order.created", "payload": {"order_id": "123"}, "source": "shopify"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "event_id" in data
        assert "status" in data

    @pytest.mark.asyncio
    async def test_receive_missing_event_type(self, client: httpx.AsyncClient) -> None:
        """POST /api/webhook/receive with empty event_type returns error."""
        resp = await client.post(
            "/api/webhook/receive",
            json={"event_type": ""},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data


class TestWebhookSubscriptions:
    """Exercise Lexigram-managed subscription and verification wiring."""

    @pytest.mark.asyncio
    async def test_create_and_verify_subscription_event(
        self, client: httpx.AsyncClient
    ) -> None:
        subscription_response = await client.post(
            "/api/webhook/subscriptions",
            json={
                "url": "https://example.test/hooks",
                "event_types": ["order.created"],
            },
        )
        assert subscription_response.status_code == 200
        subscription = subscription_response.json()
        assert subscription["active"] is True
        assert subscription["secret"]

        payload = {"order_id": "123"}
        signature = HMACSignatureVerifier().compute_signature(
            dumps(payload, sort_keys=True), subscription["secret"]
        )
        response = await client.post(
            "/api/webhook/receive",
            json={
                "event_type": "order.created",
                "payload": payload,
                "subscription_id": subscription["subscription_id"],
                "signature": signature,
            },
        )
        assert response.status_code == 200
        assert response.json()["verified"] is True

    @pytest.mark.asyncio
    async def test_list_subscriptions_hides_secrets(
        self, client: httpx.AsyncClient
    ) -> None:
        await client.post(
            "/api/webhook/subscriptions",
            json={"url": "https://example.test/hooks"},
        )
        response = await client.get("/api/webhook/subscriptions")
        assert response.status_code == 200
        item = response.json()["subscriptions"][0]
        assert "secret" not in item


class TestWebhookValidation:
    """Test webhook validation endpoints."""

    @pytest.mark.asyncio
    async def test_validate_signature(self, client: httpx.AsyncClient) -> None:
        """POST /api/webhook/validate validates a signature."""
        # First get a valid signature by receiving a webhook
        receive_resp = await client.post(
            "/api/webhook/receive",
            json={"event_type": "test.event", "payload": {"data": "test"}},
        )
        assert receive_resp.status_code == 200

        # Now validate (using a mock signature for demo purposes)
        resp = await client.post(
            "/api/webhook/validate",
            json={"payload": "test payload", "signature": "sha256=invalid"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "valid" in data

    @pytest.mark.asyncio
    async def test_validate_missing_payload(self, client: httpx.AsyncClient) -> None:
        """POST /api/webhook/validate with empty payload returns error."""
        resp = await client.post(
            "/api/webhook/validate",
            json={"payload": ""},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data


class TestWebhookEvents:
    """Test webhook event endpoints."""

    @pytest.mark.asyncio
    async def test_get_events(self, client: httpx.AsyncClient) -> None:
        """GET /api/webhook/events returns events."""
        # First receive a webhook
        await client.post(
            "/api/webhook/receive",
            json={"event_type": "test.event", "payload": {"data": "test"}},
        )

        resp = await client.get("/api/webhook/events")
        assert resp.status_code == 200
        data = resp.json()
        assert "count" in data
        assert "events" in data

    @pytest.mark.asyncio
    async def test_get_events_with_type_filter(self, client: httpx.AsyncClient) -> None:
        """GET /api/webhook/events with event_type filter returns filtered events."""
        # First receive a webhook
        await client.post(
            "/api/webhook/receive",
            json={"event_type": "filtered.event", "payload": {"data": "test"}},
        )

        resp = await client.get("/api/webhook/events?event_type=filtered.event")
        assert resp.status_code == 200
        data = resp.json()
        assert "count" in data

    @pytest.mark.asyncio
    async def test_get_event_count(self, client: httpx.AsyncClient) -> None:
        """GET /api/webhook/events/count returns event count."""
        resp = await client.get("/api/webhook/events/count")
        assert resp.status_code == 200
        data = resp.json()
        assert "count" in data


class TestHealth:
    """Test health endpoint."""

    @pytest.mark.asyncio
    async def test_health(self, client: httpx.AsyncClient) -> None:
        """GET /api/webhook/health returns ok."""
        resp = await client.get("/api/webhook/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
