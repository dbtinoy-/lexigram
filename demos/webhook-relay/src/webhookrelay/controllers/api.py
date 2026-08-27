"""Webhook API — HTTP surface for webhook relay operations.

Controllers are thin: they validate input, call a service, and
return a response dict.  No business logic lives here.
"""

from __future__ import annotations

from typing import Any

from lexigram.web import Controller, get, post


class WebhookApiController(Controller):
    """HTTP surface for webhook relay operations.

    Delegates to services for business logic.  Returns dicts that
    the framework serialises to JSON.
    """

    prefix = "/api/webhook"

    def __init__(self, validator: object = None, relay: object = None) -> None:
        self._validator = validator
        self._relay = relay

    @post("/receive")
    async def receive(self, body: dict[str, Any]) -> dict[str, Any]:
        """Receive and process a webhook.

        Body: ``{"event_type": "order.created", "payload": {...}, "source": "shopify"}``
        """
        event_type = body.get("event_type", "")
        if not event_type:
            return {"error": "Event type is required"}

        payload = body.get("payload", {})
        source = body.get("source", "unknown")

        return await self._relay.relay(event_type, payload, source)

    @post("/validate")
    async def validate(self, body: dict[str, Any]) -> dict[str, Any]:
        """Validate a webhook signature.

        Body: ``{"payload": "...", "signature": "sha256=..."}``
        """
        payload_str = body.get("payload", "")
        signature = body.get("signature", "")

        if not payload_str:
            return {"error": "Payload is required"}

        payload_bytes = payload_str.encode()
        return self._validator.validate_signature(payload_bytes, signature)

    @get("/events")
    async def events(self, event_type: str | None = None) -> dict[str, Any]:
        """Get all webhook events."""
        events = self._relay.get_events(event_type)
        return {"count": len(events), "events": events}

    @get("/events/count")
    async def event_count(self, event_type: str | None = None) -> dict[str, Any]:
        """Get webhook event count."""
        count = self._relay.get_event_count(event_type)
        return {"count": count, "event_type": event_type}

    @get("/health")
    async def health(self) -> dict[str, Any]:
        """Health check endpoint."""
        return {"status": "ok", "service": "webhookrelay"}


__all__ = ["WebhookApiController"]
