---
title: "Real-Time & WebSockets"
description: "Server-sent events, WebSocket connections, and streaming responses."
---

:::tip[Living demo]
A runnable, CI-gated companion lives at `demos/realtime-monitor/`. Try it locally:

```bash
uv run python -m ops_console
```
:::


`lexigram-web` provides WebSocket wrappers, SSE (Server-Sent Events) handlers, and streaming responses. The SSE layer includes backpressure, retry tracking, and a shared heartbeat scheduler that keeps asyncio tasks proportional to heartbeat intervals — not connection count.

For the full configuration reference and advanced features (connection lifecycle events, guard pipelines), see the [`lexigram-web` package docs](/packages/lexigram-web/).

---

## 1. WebSockets

### Basic WebSocket

The `WebSocket` class wraps Starlette's WebSocket with an ergonomic API:

```python
from lexigram.web.transport import WebSocket


async def chat_handler(ws: WebSocket) -> None:
    await ws.accept()
    try:
        while True:
            text = await ws.receive_text()
            await ws.send_json({"reply": f"Echo: {text}"})
    except Exception:
        await ws.close(code=1000)
```

Available methods:

```python
await ws.accept(subprotocol="chat")     # accept the connection
await ws.close(code=1000)               # close gracefully
text = await ws.receive_text()          # receive text frame
data = await ws.receive_json()          # receive JSON frame
await ws.send_text("hello")             # send text frame
await ws.send_json({"key": "value"})    # send JSON frame
await ws.send_bytes(data)               # send binary frame
state = ws.state                        # middleware state access
```

### Guarded WebSocket

Use `GuardedWebSocket` to enforce guards during the handshake phase. Guards run before `accept()` and reject with code `4003` on failure:

```python
from lexigram.web.transport import GuardedWebSocket, execute_websocket_guards
from lexigram.web.security import GuardProtocol


class AuthGuard(GuardProtocol):
    async def can_activate(self, ws) -> bool:
        # Check auth header, token, etc.
        return "token" in ws.headers


async def secured_chat(ws: WebSocket) -> None:
    guarded = GuardedWebSocket(ws, guards=[AuthGuard()])
    # Guards run here — rejects with 4003 if any fail
    await guarded.accept()
    ...
```

You can also run guards independently with `execute_websocket_guards()`:

```python
result = await execute_websocket_guards(guards, websocket)
if result.is_err():
    return  # connection closed by guard
```

---

## 2. Server-Sent Events (SSE)

### EventSourceResponse

The low-level `EventSourceResponse` streams events from an async generator:

```python
from typing import AsyncGenerator
from lexigram.web.transport import ServerSentEvent, EventSourceResponse
from lexigram.web import Request


async def stream_events(request: Request) -> EventSourceResponse:
    async def event_gen() -> AsyncGenerator[ServerSentEvent, None]:
        yield ServerSentEvent(data="connected", event="status")
        for i in range(10):
            yield ServerSentEvent(data=f"count: {i}", event="update", event_id=str(i))
        yield ServerSentEvent(data="done", event="complete")

    return EventSourceResponse(event_gen())
```

`ServerSentEvent` fields:

```python
ServerSentEvent(
    data=any,           # payload (str or serializable)
    event="update",     # event type name (optional)
    event_id="42",      # client-side tracking (optional)
    retry=3000,         # reconnect delay in ms (optional)
)
```

Use the `sse_response()` convenience function for the same result.

### AbstractSSEHandler

Subclass `AbstractSSEHandler` and decorate with `@sse_endpoint` for automatic connection tracking, heartbeat, and lifecycle hooks:

```python
from lexigram.web.sse import AbstractSSEHandler, sse_endpoint
from lexigram.web import Request
from collections.abc import AsyncGenerator
from typing import Any


@sse_endpoint("/events/{channel}", heartbeat_interval=15, retry=3000)
class ChannelEventsHandler(AbstractSSEHandler):
    heartbeat_interval = 15
    event_types = ["message", "join", "leave"]
    max_connections = 100

    async def stream(
        self, request: Request,
    ) -> AsyncGenerator[dict[str, Any], None]:
        channel = request.path_params["channel"]
        async for event in get_channel_events(channel):
            yield self.create_event("message", event)

    async def on_connect(self, request: Request) -> None:
        print(f"Client connected to {request.url}")

    async def on_disconnect(self, request: Request) -> None:
        print("Client disconnected")
```

Configuration via class attributes:

| Attribute | Default | Description |
|---|---|---|
| `heartbeat_interval` | `30` | Seconds between heartbeat events |
| `retry` | `3000` | Client reconnect delay in ms |
| `event_types` | `[]` | Documented event type names |
| `max_connections` | `0` | Max connections (`0` = unlimited) |

The `handle()` method manages connection limits and returns an `EventSourceResponse`:

```python
# Raise TooManyConnectionsError (503) if over limit
response = await handler.handle(request)
```

:::caution
`broadcast()` raises `NotImplementedError` — SSE is unidirectional per-client. Use a shared async queue or pub/sub channel in your `stream()` implementation to push events to multiple clients.
:::

---

## 3. Backpressure & Retry

### SSEBackpressureHandler

Buffers events up to `max_buffer_size`. Returns `False` from `send()` when the buffer is full, signalling the producer to slow down:

```python
from lexigram.web.sse import SSEBackpressureHandler


handler = SSEBackpressureHandler(max_buffer_size=100)

# Returns False if buffer full:
success = await handler.send("update", "data", event_id="42")

# Wait up to 5s for space:
has_space = await handler.wait_for_space(timeout=5.0)

# Iterate events:
async for event in handler.events():
    print(event)
```

### SSERetryTracker

Tracks `Last-Event-ID` for client-side reconnect resume:

```python
from lexigram.web.sse import SSERetryTracker


tracker = SSERetryTracker()
tracker.set_last_event_id("42")               # from request header
tracker.record_event("43", "update", "data")   # store for resume
events = tracker.get_events_after("42")         # replay on reconnect
```

### SSEResponse

Enhanced SSE with backpressure, retry tracking, and shared heartbeat:

```python
from lexigram.web.sse import SSEResponse


response = SSEResponse(
    generator=my_event_gen(),
    backpressure=True,
    max_buffer=100,
    retry_timeout=5000,
    heartbeat_interval=30.0,
)
return response.to_response()
```

---

## 4. Shared Heartbeat Scheduler

Instead of one asyncio task per connection, a single `SSEHeartbeatScheduler` fires heartbeats to all registered handlers at the configured interval:

```python
from lexigram.web.sse import SSEHeartbeatScheduler, get_heartbeat_scheduler


# Get (or create) the shared scheduler for a 30s interval:
scheduler = get_heartbeat_scheduler(interval=30.0)
await scheduler.start()  # idempotent

# Register/unregister connections:
token = await scheduler.register(handler)
await scheduler.unregister(token)

# Monitor active connections:
count = scheduler.active_connections
```

`SSEResponse` integrates this automatically — you never need to touch the scheduler directly.

---

## 5. Testing

Unit test SSE handlers by calling `stream()` directly with a request stub:

```python
from lexigram.web.sse import AbstractSSEHandler


class TestHandler(AbstractSSEHandler):
    async def stream(self, request):
        yield {"event": "test", "data": "hello"}
        yield {"event": "test", "data": "world"}


async def test_handler_streams_events() -> None:
    handler = TestHandler()
    events = [e async for e in handler._create_event_generator(mock_request)]
    assert len(events) >= 2  # +1 for initial retry event
```

For WebSocket tests, mock or stub the `WebSocket` class at the protocol boundary.

---

## Next Steps

- [Routing](/getting-started/first-app/) — controllers and route mounting basics
- [Security & Guards](/guides/authentication/) — `GuardProtocol` for WebSocket auth
- [Dependency Injection](/fundamentals/dependency-injection/) — binding protocols to implementations
- [MCP Guide](/guides/ai-mcp/) — SSE transport for the Model Context Protocol
- [`lexigram-web` package](/packages/lexigram-web/) — full config reference, decorators, middleware
