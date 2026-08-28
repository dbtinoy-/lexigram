# Queue Worker Demo

A focused, browser-first example of **Lexigram QueueModule** and
`MessageConsumer`. Publish a task to one configured topic and watch the
consumer process it in the same standalone app. It uses Lexigram's in-memory
backend, so no broker is required.

## What you'll learn

1. `QueueModule.stub()` — real `QueueProtocol` DI wiring with an in-memory backend
2. `BusMessage` — typed topic, payload, delivery guarantee, and retry metadata
3. `MessageConsumer` — subscription and automatic handler lifecycle
4. `Provider` lifecycle — start the consumer in `boot()` and stop it cleanly
5. Browser controls — publish and inspect worker progress without a CLI

## Read in order

| # | File | What you learn |
|---|------|----------------|
| 1 | `application.yaml` | Worker topic and demo configuration |
| 2 | `src/queueworker/app.py` | `QueueModule` + `WebModule` composition |
| 3 | `src/queueworker/di/provider.py` | Resolve `QueueProtocol`, start and stop the consumer |
| 4 | `src/queueworker/services/processor.py` | `MessageConsumer.handle()` implementation |
| 5 | `src/queueworker/controllers/api.py` | Publish and browser inspection endpoints |
| 6 | `src/queueworker/ui/` | Standalone task publisher and status console |
| 7 | `tests/` | Real composition-root coverage |

## Architecture

```
application.yaml
      │
      ▼
QueueModule.stub() ──► QueueProtocol ──► MessageProcessor(MessageConsumer)
      │                                      │
      └────────────── WebModule ◄────────────┘
                         │
                         ▼
                 browser console + API
```

The worker intentionally listens only to the configured `tasks` topic. This
keeps the demo about one queue-worker concern rather than turning it into a
multi-topic bus showcase.

## Quick start

```bash
cd demos/queue-worker
uv run python -m queueworker
```

Open the URL printed by the server and publish a task. The worker handles it
automatically; there is no separate process or pull-style CLI step.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/queue/publish` | Publish a `BusMessage` to the worker topic |
| `GET` | `/api/queue/processed` | Inspect the consumer audit trail |
| `GET` | `/api/queue/health` | Show topic and consumer readiness |
| `GET` | `/api/queue/size` | Show the best-effort publish/handle progress estimate |
