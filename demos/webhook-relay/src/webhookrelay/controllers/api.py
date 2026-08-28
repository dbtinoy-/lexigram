"""HTTP surface for inbound webhook verification and relay inspection."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.webhook.types import WebhookSubscription
import lexigram.serialization as json
from lexigram.web import Controller, get, post
from lexigram.webhook.subscription.service import WebhookSubscriptionService
from lexigram.webhook.verification.hmac import HMACSignatureVerifier


class WebhookApiController(Controller):
    """Keep inbound webhook handling narrow and browser-observable.

    Lexigram manages subscriptions and cryptographic verification. The demo
    adds only an in-memory event ledger so users can see accepted events
    without configuring a second server.
    """

    prefix = "/api/webhook"

    def __init__(
        self,
        relay: object = None,
        verifier: HMACSignatureVerifier | None = None,
        secret: str = "",
        max_payload_size: int = 1048576,
        subscriptions: WebhookSubscriptionService | None = None,
    ) -> None:
        self._relay = relay
        self._verifier = verifier
        self._secret = secret
        self._max_payload_size = max_payload_size
        self._subscriptions = subscriptions

    @post("/subscriptions")
    async def create_subscription(self, body: dict[str, Any]) -> dict[str, Any]:
        """Create a Lexigram-managed subscription and return its secret once."""
        url = body.get("url", "")
        if not url:
            return {"error": "URL is required"}
        event_types = body.get("event_types")
        result = await self._subscriptions.create(
            url,
            event_types=frozenset(event_types) if event_types else None,
            description=body.get("description", "Browser demo endpoint"),
        )
        if result.is_err():
            return {"error": str(result.unwrap_err())}
        return self._subscription_payload(result.unwrap(), include_secret=True)

    @get("/subscriptions")
    async def list_subscriptions(self) -> dict[str, Any]:
        """List active subscriptions without exposing shared secrets."""
        subscriptions = await self._subscriptions.list(active_only=True)
        return {
            "count": len(subscriptions),
            "subscriptions": [
                self._subscription_payload(item) for item in subscriptions
            ],
        }

    @post("/receive")
    async def receive(self, body: dict[str, Any]) -> dict[str, Any]:
        """Accept an event, optionally verifying it with a subscription secret.

        The no-signature path keeps the console one-click friendly. Supplying
        ``subscription_id`` opts into the same HMAC verification path used by
        a real inbound webhook handler.
        """
        event_type = body.get("event_type", "")
        if not event_type:
            return {"error": "Event type is required"}

        payload = body.get("payload", {})
        subscription_id = body.get("subscription_id")
        signature = body.get("signature")
        if subscription_id:
            verification = await self._verify_for_subscription(
                subscription_id,
                payload,
                signature,
            )
            if not verification["valid"]:
                return verification

        result = await self._relay.relay(
            event_type,
            payload,
            body.get("source", "unknown"),
        )
        result["verified"] = bool(subscription_id)
        return result

    @post("/validate")
    async def validate(self, body: dict[str, Any]) -> dict[str, Any]:
        """Verify a raw payload with the configured demo secret."""
        payload = body.get("payload", "")
        signature = body.get("signature", "")
        if not payload:
            return {"error": "Payload is required"}
        if len(payload.encode("utf-8")) > self._max_payload_size:
            return {"valid": False, "error": "Payload too large"}
        if not signature:
            return {"valid": False, "error": "Missing signature"}
        return {
            "valid": self._verifier.verify(
                payload.encode("utf-8"), signature, self._secret
            )
        }

    @get("/events")
    async def events(self, event_type: str | None = None) -> dict[str, Any]:
        """Get accepted events, optionally filtered by event type."""
        events = self._relay.get_events(event_type)
        return {"count": len(events), "events": events}

    @get("/events/count")
    async def event_count(self, event_type: str | None = None) -> dict[str, Any]:
        """Get the accepted-event count."""
        return {
            "count": self._relay.get_event_count(event_type),
            "event_type": event_type,
        }

    @get("/health")
    async def health(self) -> dict[str, Any]:
        """Report that the relay and Lexigram subscription service are ready."""
        return {"status": "ok", "service": "webhookrelay", "subscriptions": True}

    async def _verify_for_subscription(
        self,
        subscription_id: str,
        payload: dict[str, Any],
        signature: str | None,
    ) -> dict[str, Any]:
        """Verify a canonical JSON payload against a stored subscription secret."""
        if not signature:
            return {"valid": False, "error": "Missing signature"}
        result = await self._subscriptions.get(subscription_id)
        if result.is_err():
            return {"valid": False, "error": str(result.unwrap_err())}
        subscription = result.unwrap()
        raw_payload = json.dumps(payload, sort_keys=True)
        return {
            "valid": self._verifier.verify(
                raw_payload,
                signature,
                subscription.secret,
            ),
            "subscription_id": subscription_id,
        }

    @staticmethod
    def _subscription_payload(
        subscription: WebhookSubscription,
        *,
        include_secret: bool = False,
    ) -> dict[str, Any]:
        """Convert a package subscription to JSON-safe demo output."""
        value: dict[str, Any] = {
            "subscription_id": subscription.subscription_id,
            "url": subscription.url,
            "event_types": sorted(subscription.event_types)
            if subscription.event_types
            else None,
            "active": subscription.active,
            "description": subscription.description,
            "created_at": subscription.created_at.isoformat(),
        }
        if include_secret:
            value["secret"] = subscription.secret
        return value


__all__ = ["WebhookApiController"]
