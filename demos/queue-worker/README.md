# Queue Worker Demo

Teaches Lexigram queue pattern — in-memory message queue, message consumers,
and background task processing.

## Read in order

| # | File | What you learn |
|---|------|----------------|
| 1 | `application.yaml` | Configuration — queue settings |
| 2 | `src/queueworker/app.py` | Composition root — module wiring |
| 3 | `src/queueworker/di/provider.py` | Provider lifecycle — register, boot, shutdown |
| 4 | `src/queueworker/queue.py` | In-memory queue implementation |
| 5 | `src/queueworker/services/processor.py` | Message processing patterns |
| 6 | `tests/` | Real composition root, no mocks |

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
