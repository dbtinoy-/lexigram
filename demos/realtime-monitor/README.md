# Realtime Monitor Demo

> Module name: `ops_console` — run with `uv run python -m ops_console`

Demonstrates the **real-time web** subsystem of Lexigram.

This demo is a small production-style ops console. System events stream into a
browser dashboard over **Server-Sent Events (SSE)**. An operator can connect
over a **WebSocket** channel and publish events straight into the same stream
so every dashboard updates live. No external services, databases, or CDN
assets are required — the browser client is a dependency-free `EventSource`.

## What it shows

| Piece | Where | Lexigram API used |
|-------|-------|-------------------|
| In-process pub/sub bus with history replay and bounded queues | `src/ops_console/services/event_stream.py` | plain `asyncio` primitives |
| SSE streaming endpoint (replay-then-live + heartbeats) | `src/ops_console/controllers/console.py` | `AbstractSSEHandler`, `EventSourceResponse` |
| HTTP publish endpoint (`POST /api/events`) | `src/ops_console/controllers/console.py` | `Controller` + `@get` / `@post` |
| WebSocket operator channel (bidirectional) | `src/ops_console/controllers/operator.py` | `AbstractWebSocketHandler` |
| Dashboard page (vanilla JS `EventSource`, no frameworks) | `src/ops_console/controllers/console.py` | `lexigram.ui` + `HTMLContent` |
| DI wiring + heartbeat producer + route hookup | `src/ops_console/di/provider.py` | `Provider`, provider lifecycle priorities |

## Run it

```bash
uv run python -m ops_console                 # serves http://127.0.0.1:7071
```

Open http://127.0.0.1:7071 in two browsers — you should see the same live
heartbeats appear in both. Then push a manual event:

```bash
uv run python -m ops_console --publish --message "deploy request approved"
```

Big picture: the SSE handler replays recent history for a brand-new subscriber,
so a dashboard that connects late still renders the latest state instead of a
blank page. The WebSocket channel lets an operator (or a script) inject events
without refreshing or reloading anything.

## Layout

```
demos/realtime-monitor/
├── src/ops_console/
│   ├── domain.py                 # SystemEvent value type + Severity enum
│   ├── services/event_stream.py  # EventStreamService (pub/sub + replay)
│   ├── controllers/
│   │   ├── console.py            # dashboard + SSE + HTTP publish
│   │   └── operator.py           # WebSocket operator handler
│   ├── di/provider.py            # RealtimeProvider (wiring + heartbeat)
│   ├── module.py                 # RealtimeModule (binds web layer)
│   └── main.py                   # server + publish CLI
└── tests/                        # pytest suite (asyncio mode auto)
```

## Tests

```bash
uv run pytest demos/realtime-monitor/tests -q
```

The tests cover the bus in isolation (fan-out to many subscribers, replay for
late subscribers, and the drop-oldest behavior for slow consumers), plus HTTP
and WebSocket endpoints exercised through a Starlette `TestClient`.

## Known boot noise

On startup the server may log one
`web.contributor_mount_failed ... 'admin_bundle'` error. This comes from
**optional-package contributor discovery**: any installed package that
declares a `lexigram.admin.contributors` entry point (today:
`lexigram-auth`) is loaded into every web app's registry, and its mount
resolves an admin bundle only the full admin application registers. The
failure is isolated by design — the demo neither imports nor needs the admin
panel, and serving is unaffected.