# Monitor Stack Demo

Teaches the **Lexigram monitoring pattern** — in-memory metrics, health
checks, tracing, and observability decorators.  Demonstrates observability
patterns without requiring external monitoring services.

## What you'll learn

1. **Health checks** — registering and running health check functions
2. **Metrics collection** — counters, gauges, and histograms
3. **Request tracing** — trace spans with timing
4. **Provider wiring** — injecting monitoring services via DI

## Read in order

| # | File | What you learn |
|---|------|----------------|
| 1 | `application.yaml` | Configuration — service name, health interval, metrics toggle |
| 2 | `src/monitorstack/app.py` | Composition root — `build_modules()` + `build_providers()` |
| 3 | `src/monitorstack/di/provider.py` | Provider lifecycle — `register()`, `boot()`, `health_check()` |
| 4 | `src/monitorstack/config.py` | Config model — `BaseConfig` + `Field()` with descriptions |
| 5 | `src/monitorstack/metrics.py` | In-memory metrics — counters, gauges, histograms |
| 6 | `src/monitorstack/services/health.py` | Health checker — register and run health checks |
| 7 | `src/monitorstack/services/tracer.py` | Request tracing — trace spans with timing |
| 8 | `src/monitorstack/controllers/api.py` | HTTP surface — thin controller adapters |
| 9 | `tests/` | Real composition root, no mocks |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      application.yaml                           │
│  web: server/host/port, security/csrf/enabled                  │
│  monitorstack: service_name, health_check_interval, metrics_enabled│
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                         app.py                                  │
│  build_modules()  → [WebModule.configure(controllers=[...])]    │
│  build_providers() → [MonitorStackProvider()]                   │
│  create_app()     → Application(name="monitor-stack")          │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      provider.py                                │
│  register(): container.singleton(MonitorStackConfig, instance=cfg)│
│  boot():     resolve config → create metrics/health/tracer → bind│
└─────────────────────────────────────────────────────────────────┘
```

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

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/monitor/health` | Run health checks |
| `GET` | `/api/monitor/health/self` | Self health check |
| `GET` | `/api/monitor/metrics` | Get all metrics |
| `POST` | `/api/monitor/metrics/increment` | Increment a counter |
| `POST` | `/api/monitor/metrics/gauge` | Set a gauge |
| `GET` | `/api/monitor/traces` | Get trace spans |
| `POST` | `/api/monitor/trace` | Create a trace span |
| `GET` | `/api/monitor/health` | Health check |
