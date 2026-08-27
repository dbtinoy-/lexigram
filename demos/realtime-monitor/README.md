# Realtime Monitor Demo

> Module name: `ops_console` — run with `PYTHONPATH=src uv run python -m ops_console`

Demonstrates the **real-time web** subsystem of Lexigram.

This demo is a small production-style ops console. System events stream into a
browser dashboard over **Server-Sent Events (SSE)**. An operator can connect
over a **WebSocket** channel and publish events straight into the same stream
so every dashboard updates live. No external services, databases, or CDN
assets are required — the browser client is a dependency-free `EventSource`.

## Lexigram concepts used

| Concept | Where in this demo | Your app |
|---------|-------------------|----------|
| Composition root | `app.py` | Replace controllers/providers list |
| Provider lifecycle | `di/provider.py` | register() binds, boot() initializes heartbeat |
| SSE streaming | `controllers/console.py` | `AbstractSSEHandler` for real-time push |
| WebSocket handler | `controllers/operator.py` | `AbstractWebSocketHandler` for bidirectional |
| Custom config model | `config.py` → `RealtimeConfig` | Add demo-specific knobs in `demo:` section |
| Event bus | `services/event_stream.py` | In-memory pub/sub with replay |

## What it shows

| Piece | Where | Lexigram API used |
|-------|-------|-------------------|
| In-process pub/sub bus with history replay and bounded queues | `services/event_stream.py` | plain `asyncio` primitives |
| SSE streaming endpoint (replay-then-live + heartbeats) | `controllers/console.py` | `AbstractSSEHandler`, `EventSourceResponse` |
| HTTP publish endpoint (`POST /api/events`) | `controllers/console.py` | `Controller` + `@get` / `@post` |
| WebSocket operator channel (bidirectional) | `controllers/operator.py` | `AbstractWebSocketHandler` |
| Dashboard page (vanilla JS `EventSource`, no frameworks) | `ui/pages.py` | `lexigram.ui` + `HTMLContent` |
| DI wiring + heartbeat producer + route hookup | `di/provider.py` | `Provider`, provider lifecycle priorities |

## Run it

```bash
cd demos/realtime-monitor
PYTHONPATH=src uv run python -m ops_console
```

Open http://127.0.0.1:7071 in two browsers — you should see the same live
heartbeats appear in both. Then push a manual event:

```bash
PYTHONPATH=src uv run python -m ops_console --publish --message "deploy request approved"
```

## Layout — read it in this order

| # | File | Lesson |
|---|------|--------|
| 1 | `src/ops_console/app.py` | ⭐ Composition root: config → modules → providers |
| 2 | `src/ops_console/main.py` | Lifecycle: `Application.start/stop`, CLI publish |
| 3 | `src/ops_console/di/provider.py` | DI wiring: register() binds, boot() starts heartbeat |
| 4 | `src/ops_console/config.py` | Custom config model: `RealtimeConfig` for `demo:` section |
| 5 | `src/ops_console/services/event_stream.py` | Event bus: pub/sub, replay, bounded queues |
| 6 | `src/ops_console/controllers/console.py` | SSE streaming + HTTP publish endpoint |
| 7 | `src/ops_console/controllers/operator.py` | WebSocket operator channel |
| 8 | `application.yaml` | Web + demo config sections |

```
demos/realtime-monitor/
├── src/ops_console/
│   ├── app.py                 # ⭐ composition root (start here)
│   ├── main.py                # entry point / lifecycle + CLI publish
│   ├── config.py              # RealtimeConfig for demo: section
│   ├── domain.py              # SystemEvent value type + Severity enum
│   ├── di/
│   │   └── provider.py        # RealtimeProvider (wiring + heartbeat)
│   ├── controllers/
│   │   ├── console.py         # dashboard + SSE + HTTP publish
│   │   └── operator.py        # WebSocket operator handler
│   ├── services/
│   │   └── event_stream.py    # EventStreamService (pub/sub + replay)
│   └── ui/
│       └── pages.py           # Dashboard HTML page
├── application.yaml           # web + demo sections (LEX_* overrides win)
└── tests/                     # bus isolation + HTTP/WebSocket tests
```

## Tests

```bash
uv run pytest demos/realtime-monitor/tests -q
```
