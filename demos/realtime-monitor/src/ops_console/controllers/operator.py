"""WebSocket operator channel for the realtime monitor demo.

Subclasses :class:`AbstractWebSocketHandler` so the framework owns the full
connection lifecycle (accept, message loop, disconnect cleanup). The handler
pushes each received JSON payload into the shared :class:`EventStreamService`
so every SSE dashboard and the operator room see the same events.
"""

from __future__ import annotations

from typing import Any

from lexigram.web import WebSocket
from lexigram.web.websocket.handler import AbstractWebSocketHandler
from ops_console.domain import Severity, SystemEvent
from ops_console.services.event_stream import EventStreamService


class OperatorHandler(AbstractWebSocketHandler):
    """Publish operator messages into the event stream."""

    def __init__(self, events: EventStreamService) -> None:
        super().__init__()
        self.events = events

    async def on_connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        await websocket.send_json({"ok": True, "message": "operator channel connected"})

    async def on_message(self, websocket: WebSocket, message: dict[str, Any]) -> None:
        event = SystemEvent(
            kind="operator",
            message=str(message.get("message") or "operator event"),
            severity=Severity.from_name(str(message.get("severity") or "info")),
            source="operator-channel",
            payload={"echo": True},
        )
        await self.events.publish(event)
        await websocket.send_json({"ok": True, "severity": event.severity.value})

    async def on_disconnect(self, websocket: WebSocket) -> None:
        return


__all__ = ["OperatorHandler"]
