# Monitor Stack Demo

Teaches Lexigram monitoring pattern — in-memory metrics, health checks,
tracing, and observability decorators.

## Read in order

| # | File | What you learn |
|---|------|----------------|
| 1 | `application.yaml` | Configuration — monitoring settings |
| 2 | `src/monitorstack/app.py` | Composition root — module wiring |
| 3 | `src/monitorstack/di/provider.py` | Provider lifecycle — register, boot, shutdown |
| 4 | `src/monitorstack/metrics.py` | In-memory metrics implementation |
| 5 | `src/monitorstack/services/` | Health checks and tracing patterns |
| 6 | `tests/` | Real composition root, no mocks |

## Quick start

```bash
cd demos/monitor-stack
uv run python -m monitorstack
```

## Run tests

```bash
cd demos/monitor-stack
uv run pytest tests/ -v
```
