"""Realtime monitor controllers.

The dashboard page plus the HTTP endpoints that back it:

- ``GET /`` — the dashboard page (vanilla ``EventSource`` client, no external
  dependencies).
- ``GET /api/events/stream`` — server-sent events: replay recent history then
  stream live events (with heartbeats).
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
from typing import Any

from lexigram.ui import el, render_to_string
from lexigram.web import Controller, HTMLContent, get, post
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

    async def stream(self, request) -> AsyncGenerator[dict[str, Any], None]:
        async for event in self.events.subscribe():
            yield {"event": event.kind, "data": event.to_dict()}


def _render_event_row(event: SystemEvent) -> str:
    """Render one event as an HTML table row for the dashboard feed."""
    return render_to_string(
        el(
            "tr",
            el(
                "td",
                event.occurred_at.strftime("%H:%M:%S"),
                class_="text-slate-400 text-sm",
            ),
            el(
                "td",
                el(
                    "span",
                    event.severity.value.upper(),
                    class_=(
                        "font-mono text-xs px-2 py-0.5 rounded "
                        + {
                            Severity.CRITICAL: "bg-red-600/20 text-red-300",
                            Severity.WARN: "bg-amber-500/20 text-amber-300",
                            Severity.INFO: "bg-sky-500/20 text-sky-300",
                        }[event.severity]
                    ),
                ),
                class_="pr-4",
            ),
            el(
                "td",
                f"{event.source} · {event.kind}",
                class_="font-mono text-sm text-slate-300",
            ),
            el(
                "td",
                event.message,
                class_="text-slate-200",
            ),
            class_="border-b border-slate-800",
        )
    )


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

    @get("/")
    async def dashboard(self, request=None) -> HTMLContent:
        rows = "\n".join(_render_event_row(event) for event in self.events.snapshot())
        stats = self.events.stats()
        page = render_to_string(
            el(
                "html",
                el(
                    "head",
                    el("title", "Realtime Console"),
                    el(
                        "style",
                        "body{font-family:ui-monospace,monospace;background:#0b1120;"
                        "color:#e2e8f0;margin:0;padding:2rem}"
                        "table{border-collapse:collapse;width:100%}"
                        "th{text-align:left;color:#94a3b8;padding-bottom:.5rem}"
                        "form{display:flex;gap:.5rem;margin:1rem 0}",
                    ),
                ),
                el(
                    "body",
                    el("h1", "Realtime Console", class_="text-2xl font-bold"),
                    el(
                        "p",
                        "Live system events streamed over SSE. Subscribers: ",
                        el("span", str(stats.subscribers), id="subscribers"),
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
                        el("tbody", rows, id="events"),
                    ),
                    el(
                        "form",
                        el("input", name="message", placeholder="Event message…"),
                        el(
                            "input",
                            name="source",
                            placeholder="source",
                            value="console",
                        ),
                        el("button", "Publish", type="submit"),
                        el("input", type="hidden", name="severity", value="info"),
                        id="publish-form",
                    ),
                    el(
                        "script",
                        """const es = new EventSource('/api/events/stream');
es.addEventListener('open', () => console.log('connected'));
es.addEventListener('error', () => es.close());
es.onmessage = (e) => {
  const row = document.createElement('tr');
  row.className = 'border-b border-slate-800';
  const d = JSON.parse(e.data);
  row.innerHTML = '<td class="text-slate-400 text-sm">' + d.occurred_at.slice(11, 19) +
    '</td><td class="font-mono text-xs text-sky-300 pr-4">' + d.severity.toUpperCase() +
    '</td><td class="font-mono text-sm text-slate-300">' + d.source + ' · ' + d.kind +
    '</td><td class="text-slate-200">' + d.message + '</td>';
  document.getElementById('events').prepend(row);
};
const form = document.getElementById('publish-form');
form.addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const data = new FormData(form);
  const msg = data.get('message');
  await fetch('/api/events', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message: msg, severity: 'info', source: data.get('source')})
  });
  form.reset();
});
""",
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
