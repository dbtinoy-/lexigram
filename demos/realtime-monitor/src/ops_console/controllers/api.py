"""Realtime monitor controllers.

The HTTP endpoints that back the dashboard:

- ``GET /api/events/stream`` — server-sent events: replay recent history then
  stream live events (with heartbeats).
- ``GET /api/stats`` — live subscriber and history counts for the header chips.
- ``POST /api/events`` — publish an event from an external tool or curl.

The dashboard page and static assets are served by
:class:`ops_console.ui.pages.PagesController`; the WebSocket operator channel
is owned by :class:`OperatorHandler`.

The SSE handler is a normal container service; the controller method simply
hands the incoming request to it. This keeps route registration inside the
familiar ``Controller`` flow while the handler stays framework-agnostic.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from starlette.requests import Request

from lexigram.serialization import loads as json_loads
from lexigram.web import Controller, get, post
from lexigram.web.sse.handler import AbstractSSEHandler
from ops_console.domain import Severity, SystemEvent
from ops_console.services.event_stream import EventStreamService


class EventsStreamHandler(AbstractSSEHandler):
    """SSE handler that replays history and then streams live events."""

    heartbeat_interval = 15
    retry = 3000

    def __init__(self, events: EventStreamService) -> None:
        super().__init__()
        self.events = events

    async def stream(self, request: Request) -> AsyncGenerator[dict[str, Any], None]:
        async for event in self.events.subscribe():
            yield {"event": event.kind, "data": event.to_dict()}


class ConsoleController(Controller):
    """SSE streaming plus the stats and publish endpoints."""

    def __init__(
        self,
        events: EventStreamService,
        sse: EventsStreamHandler,
    ) -> None:
        self.events = events
        self.sse = sse

    @get("/api/events/stream")
    async def stream(self, request: Request | None = None) -> Any:
        return await self.sse.handle(request)

    @get("/api/stats")
    async def stats(self, request: Request | None = None) -> dict[str, Any]:
        """Return live subscriber and history counts for the dashboard chips."""
        stats = self.events.stats()
        return {"subscribers": stats.subscribers, "history": stats.events}

    @post("/api/events")
    async def publish_event(self, request: Request | None = None) -> dict[str, Any]:
        body = json_loads(await request.body())
        event = SystemEvent(
            kind="manual",
            message=str(body.get("message") or "no message"),
            severity=Severity.from_name(str(body.get("severity") or "info")),
            source=str(body.get("source") or "console"),
            payload={"operator": True},
        )
        subscribers = await self.events.publish(event)
        return {"ok": True, "subscribers": subscribers}


__all__ = ["ConsoleController", "EventsStreamHandler"]
