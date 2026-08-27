# Queue Worker Demo

Teaches the **Lexigram queue pattern** — in-memory message queue, message
consumers, and background task processing.  Demonstrates publish/consume
patterns without requiring an external message broker.

## What you'll learn

1. **In-memory queue** — publish and consume messages with topic routing
2. **Message processing** — single and batch message processing
3. **Provider wiring** — injecting queue services via DI
4. **Test bootstrap** — real composition root, no mocks

## Read in order

| # | File | What you learn |
|---|------|----------------|
| 1 | `application.yaml` | Configuration — queue name, retries, batch size |
| 2 | `src/queueworker/app.py` | Composition root — `build_modules()` + `build_providers()` |
| 3 | `src/queueworker/di/provider.py` | Provider lifecycle — `register()`, `boot()`, `health_check()` |
| 4 | `src/queueworker/config.py` | Config model — `BaseConfig` + `Field()` with descriptions |
| 5 | `src/queueworker/queue.py` | In-memory queue — publish, consume, peek, size |
| 6 | `src/queueworker/services/processor.py` | Message processing — single and batch |
| 7 | `src/queueworker/controllers/api.py` | HTTP surface — thin controller adapters |
| 8 | `tests/` | Real composition root, no mocks |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      application.yaml                           │
│  web: server/host/port, security/csrf/enabled                  │
│  queueworker: queue_name, max_retries, batch_size              │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                         app.py                                  │
│  build_modules()  → [WebModule.configure(controllers=[...])]    │
│  build_providers() → [QueueWorkerProvider()]                    │
│  create_app()     → Application(name="queue-worker")           │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      provider.py                                │
│  register(): container.singleton(QueueWorkerConfig, instance=cfg)│
│  boot():     resolve config → create queue → bind controller    │
└─────────────────────────────────────────────────────────────────┘
```

## Quick start

```bash
cd demos/queue-worker
uv run python -m queueworker
```

## Run tests

```bash
cd demos/queue-worker
uv run pytest tests/ -v
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/queue/publish` | Publish a message to the queue |
| `POST` | `/api/queue/process` | Process a single message |
| `POST` | `/api/queue/process/batch` | Process a batch of messages |
| `GET` | `/api/queue/size` | Get queue size |
| `GET` | `/api/queue/processed` | Get processed messages |
| `GET` | `/api/queue/health` | Health check |
