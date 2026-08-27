"""Webhook relay — routes and relays webhook payloads."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class WebhookEvent:
    """A processed webhook event."""

    id: str
    source: str
    event_type: str
    payload: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    status: str = "pending"


class WebhookRelay:
    """Routes and relays webhook payloads.

    Demonstrates webhook relay patterns with event routing.
    """

    def __init__(self) -> None:
        self._events: list[WebhookEvent] = []
        self._routes: dict[str, Any] = {}

    def register_route(self, event_type: str, handler: Any) -> None:
        """Register a route for an event type."""
        self._routes[event_type] = handler

    async def relay(
        self, event_type: str, payload: dict[str, Any], source: str = "unknown"
    ) -> dict[str, Any]:
        """Relay a webhook event."""
        event_id = f"evt_{len(self._events) + 1}"
        event = WebhookEvent(
            id=event_id,
            source=source,
            event_type=event_type,
            payload=payload,
        )

        # Check for registered route
        handler = self._routes.get(event_type)
        if handler:
            try:
                result = await handler(payload)
                event.status = "delivered"
                return {"event_id": event_id, "status": "delivered", "result": result}
            except Exception as e:
                event.status = "failed"
                return {"event_id": event_id, "status": "failed", "error": str(e)}

        # No route registered, just log the event
        event.status = "logged"
        self._events.append(event)
        return {"event_id": event_id, "status": "logged"}

    def get_events(self, event_type: str | None = None) -> list[dict[str, Any]]:
        """Get all events, optionally filtered by type."""
        events = self._events
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return [
            {
                "id": e.id,
                "source": e.source,
                "event_type": e.event_type,
                "timestamp": e.timestamp,
                "status": e.status,
            }
            for e in events
        ]

    def get_event_count(self, event_type: str | None = None) -> int:
        """Get event count."""
        return len(self.get_events(event_type))
