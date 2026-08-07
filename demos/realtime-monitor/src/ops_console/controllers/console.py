"""Realtime monitor controllers.

The dashboard page plus the HTTP endpoints that back it:

- ``GET /`` — the dashboard page (vanilla ``EventSource`` client, no external
  dependencies).
- ``GET /api/events/stream`` — server-sent events: replay recent history then
  stream live events (with heartbeats).
- ``GET /api/stats`` — live subscriber and history counts for the header chips.
- ``POST /api/events`` — publish an event from an external tool or curl.

The WebSocket operator channel is owned by :class:`OperatorHandler` and is
hooked into the router by :class:`RealtimeProvider` — keep HTTP and WS wiring
in their natural homes and let the DI provider connect them.

The SSE handler is a normal container service; the controller method simply
hands the incoming request to it. This keeps route registration inside the
familiar ``Controller`` flow while the handler stays framework-agnostic.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from lexigram.serialization import dumps_str
from lexigram.ui import el, raw, render_to_string
from lexigram.web import Controller, FileResponse, HTMLContent, get, post
from lexigram.web.sse.handler import AbstractSSEHandler
from ops_console.domain import Severity, SystemEvent
from ops_console.services.event_stream import EventStreamService

JAVASCRIPT_PATH = Path(__file__).resolve().parent.parent / "static" / "dashboard.js"
STYLESHEET_PATH = Path(__file__).resolve().parent.parent / "static" / "style.css"


class EventsStreamHandler(AbstractSSEHandler):
    """SSE handler that replays history and then streams live events."""

    heartbeat_interval = 15
    retry = 3000

    def __init__(self, events: EventStreamService) -> None:
        super().__init__()
        self.events = events

    async def stream(self, request) -> AsyncGenerator[dict[str, Any], None]:
        async for event in self.events.subscribe():
            yield {"event": event.kind, "data": event.to_dict()}


class ConsoleController(Controller):
    """Dashboard page plus the SSE streaming and publish endpoints."""

    def __init__(
        self,
        events: EventStreamService,
        sse: EventsStreamHandler,
    ) -> None:
        self.events = events
        self.sse = sse

    @get("/api/events/stream")
    async def stream(self, request=None) -> Any:
        return await self.sse.handle(request)

    @get("/api/stats")
    async def stats(self, request=None) -> dict[str, Any]:
        """Return live subscriber and history counts for the dashboard chips."""
        stats = self.events.stats()
        return {"subscribers": stats.subscribers, "history": stats.events}

    @get("/static/dashboard.js")
    async def dashboard_js(self, request=None) -> FileResponse:
        """Serve the dashboard client script as a real JavaScript asset."""
        return FileResponse(path=JAVASCRIPT_PATH, media_type="text/javascript")

    @get("/static/style.css")
    async def dashboard_css(self, request=None) -> FileResponse:
        """Serve the dashboard stylesheet as a real CSS asset."""
        return FileResponse(path=STYLESHEET_PATH, media_type="text/css")

    @get("/")
    async def dashboard(self, request=None) -> HTMLContent:
        stats = self.events.stats()
        history = [event.to_dict() for event in self.events.snapshot()]
        seed_json = dumps_str(history).replace("</", "<\\/")
        page = render_to_string(
            el(
                "html",
                el(
                    "head",
                    el("title", "Realtime Console"),
                    el("link", rel="stylesheet", href="/static/style.css"),
                ),
                el(
                    "body",
                    el(
                        "div",
                        el(
                            "div",
                            el("h1", "Realtime Console", class_="accent"),
                            el(
                                "div",
                                el("span", "", class_="dot", id="conn-dot"),
                                el("span", "Connecting…", id="conn-label"),
                                class_="conn",
                            ),
                            el(
                                "span",
                                "subs: ",
                                el("b", str(stats.subscribers), id="subs"),
                                class_="chip",
                            ),
                            el(
                                "span",
                                "history: ",
                                el("b", str(stats.events), id="hist"),
                                class_="chip",
                            ),
                            el("span", "♥ ", el("b", "—", id="beat"), class_="chip"),
                            class_="topbar",
                        ),
                        el(
                            "div",
                            el(
                                "input",
                                placeholder="Search events…",
                                id="search",
                                class_="search",
                                type="search",
                            ),
                            el(
                                "select",
                                el("option", "All severities", value="all"),
                                el("option", "Info", value="info"),
                                el("option", "Warn", value="warn"),
                                el("option", "Critical", value="critical"),
                                id="filter-sev",
                            ),
                            el("button", "Pause", id="pause"),
                            el("button", "Clear feed", id="clear"),
                            class_="toolbar",
                        ),
                        el(
                            "table",
                            el(
                                "thead",
                                el(
                                    "tr",
                                    el("th", "Time"),
                                    el("th", "Severity"),
                                    el("th", "Source"),
                                    el("th", "Message"),
                                ),
                            ),
                            el(
                                "tbody",
                                el("tr", el("td", "Loading…", colspan="4"), id="empty"),
                                id="events",
                            ),
                        ),
                        el(
                            "script",
                            raw(seed_json),
                            type="application/json",
                            id="feed-data",
                        ),
                        el(
                            "form",
                            el(
                                "input",
                                placeholder="Event message…",
                                id="msg",
                                required="",
                            ),
                            el(
                                "input",
                                placeholder="source",
                                value="console",
                                id="src",
                            ),
                            el(
                                "select",
                                el("option", "info", value="info"),
                                el("option", "warn", value="warn"),
                                el("option", "critical", value="critical"),
                                id="sev",
                            ),
                            el("button", "Publish", id="publish-btn", type="submit"),
                            class_="publish",
                            id="publish-form",
                        ),
                        el("script", src="/static/dashboard.js"),
                        class_="wrap",
                    ),
                ),
            )
        )
        return HTMLContent(page)

    @post("/api/events")
    async def publish_event(self, request=None) -> dict[str, Any]:
        body = await request.json()
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
