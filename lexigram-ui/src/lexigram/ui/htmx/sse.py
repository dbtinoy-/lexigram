"""SSE support for Lexigram UI.

Server-side:  ``SSEMessage``, ``SSEStream`` — format and stream SSE payloads.
Client-side:  ``SSE`` component — renders the HTMX SSE connector element with
              typed event names and automatic exponential-backoff reconnection.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from enum import Enum
from typing import Any

from starlette.responses import StreamingResponse

from lexigram.serialization import dumps_str
from lexigram.ui.core.base import Component, el, raw

__all__ = [
    "SSEEventType",
    "SSEMessage",
    "SSEStream",
    "SSE",
]


# ---------------------------------------------------------------------------
# Typed event names
# ---------------------------------------------------------------------------


class SSEEventType(str, Enum):
    """Well-known SSE event type names.

    Use these instead of bare strings when configuring the ``SSE`` component
    or emitting ``SSEMessage`` objects so the names stay in sync across the
    client and server.
    """

    MESSAGE = "message"
    UPDATE = "update"
    ERROR = "error"
    PING = "ping"
    CLOSE = "close"
    CONNECT = "connect"
    DISCONNECT = "disconnect"


# ---------------------------------------------------------------------------
# Server-side helpers
# ---------------------------------------------------------------------------


class SSEMessage:
    """Helper to format SSE messages."""

    def __init__(
        self,
        data: Any,
        event: str | None = None,
        event_id: str | None = None,
        retry: int | None = None,
    ):
        self.data = data
        self.event = event
        self.id = event_id
        self.retry = retry

    def __str__(self) -> str:
        lines = []
        if self.id:
            lines.append(f"id: {self.id}")
        if self.event:
            lines.append(f"event: {self.event}")
        if self.retry:
            lines.append(f"retry: {self.retry}")

        data = self.data
        if not isinstance(data, str):
            data = dumps_str(data)

        for line in data.split("\n"):
            lines.append(f"data: {line}")

        return "\n".join(lines) + "\n\n"


class SSEStream(StreamingResponse):
    """Streaming response for Server-Sent Events."""

    def __init__(self, generator: AsyncGenerator[SSEMessage, None], **kwargs: Any):
        async def event_generator() -> Any:
            try:
                async for message in generator:
                    yield str(message)
            except asyncio.CancelledError:
                pass

        super().__init__(event_generator(), media_type="text/event-stream", **kwargs)
        self.headers["Cache-Control"] = "no-cache"
        self.headers["Connection"] = "keep-alive"
        self.headers["X-Accel-Buffering"] = "no"


# ---------------------------------------------------------------------------
# Client-side HTMX SSE connector component
# ---------------------------------------------------------------------------


class SSE(Component):
    """Client-side HTMX SSE connector with typed event support and auto-reconnect.

    Renders a ``<div>`` wired up with the ``hx-ext="sse"`` extension plus an
    inline ``<script>`` that listens for ``htmx:sseError`` and schedules a
    reconnect with exponential back-off, capped at 30 s.

    Args:
        url: SSE endpoint URL (``sse-connect`` attribute).
        target: CSS selector or ``"this"`` for the HTMX swap target.
        event_type: SSE event name to swap on (``sse-swap`` attribute).
            Accepts a plain string or an ``SSEEventType`` member.
        retry_ms: Initial reconnect delay in milliseconds (default 3000).
            Doubles on each failed attempt, capped at 30 000 ms.
    """

    def __init__(
        self,
        url: str,
        target: str = "this",
        event_type: str = SSEEventType.MESSAGE,
        retry_ms: int = 3000,
        **props: Any,
    ) -> None:
        super().__init__(
            url=url, target=target, event_type=event_type, retry_ms=retry_ms, **props
        )
        self.url = url
        self.target = target
        # Normalise SSEEventType members to their string value
        self.event_type = (
            event_type.value if isinstance(event_type, SSEEventType) else event_type
        )
        self.retry_ms = max(100, int(retry_ms))

    def render(self) -> Any:
        # Use the Python object id to produce a unique DOM id per render.
        component_id = f"sse-{id(self)}"

        reconnect_script = raw(
            f"<script>"
            f"(function(){{"
            f"var _el=document.getElementById('{component_id}');"
            f"var _retry={self.retry_ms};"
            f"var _max=30000;"
            f"var _n=0;"
            f"document.addEventListener('htmx:sseError',function(e){{"
            f"if(!_el||!e.detail)return;"
            f"var delay=Math.min(_retry*Math.pow(2,_n),_max);"
            f"_n++;"
            f"setTimeout(function(){{if(_el&&typeof htmx!=='undefined')htmx.process(_el);}},delay);"
            f"}});"
            f"document.addEventListener('htmx:sseOpen',function(){{{{"
            f"_n=0;"
            f"}}}});"
            f"}})();"
            f"</script>"
        )

        return el(
            "div",
            {
                "id": component_id,
                "hx-ext": "sse",
                "sse-connect": self.url,
                "sse-swap": self.event_type,
                "hx-target": self.target,
            },
            *self.children,
            reconnect_script,
        )
