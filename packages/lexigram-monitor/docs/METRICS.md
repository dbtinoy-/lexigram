---
title: lexigram-monitor Metrics
description: Metric types, built-in metrics, custom metrics, health checks, and tracing span attributes.
---

> **Alpha (0.1.x)** — MIT licensed. Public API may change before 1.0.

## Available metric types

| Type | Class | Behavior | Use case |
|------|-------|----------|----------|
| **Counter** | `from lexigram.monitor.metrics import Counter` | Monotonically increasing | Request count, error count |
| **Gauge** | `from lexigram.monitor.metrics import Gauge` | Up/down value | Active connections, queue depth |
| **Histogram** | `from lexigram.monitor.metrics import Histogram` | Value distribution with buckets | Request latency, payload size |
| **Summary** | `from lexigram.monitor.metrics import Summary` | Quantile-based distribution | SLA tracking (p50, p95, p99) |

All types are created via the `MetricsCollectorProtocol`:

```python
from lexigram.contracts.observability.metrics import MetricsCollectorProtocol

collector = await container.resolve(MetricsCollectorProtocol)

counter = collector.create_counter("api_requests_total", "Total API requests")
gauge = collector.create_gauge("active_connections", "Active connections")
histogram = collector.create_histogram(
    "request_duration_seconds", "Request duration",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
)
```

## Built-in metrics

`MonitorProvider` registers these default metrics on boot:

| Metric name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `lexigram_requests_total` | Counter | `method`, `status` | Total HTTP requests |
| `lexigram_request_duration_seconds` | Histogram | `method` | Request latency distribution |
| `lexigram_active_connections` | Gauge | — | Current active connections |
| `lexigram_hook_events_total` | Counter | `hook`, `package` | Hook-triggered events |

These are automatically created and wired when `MonitorProvider.boot()` runs. If you register a `HookRegistryProtocol`, the monitor subscribes to framework hooks and emits the `lexigram_hook_events_total` counter with per-hook labels.

## Backend-specific considerations

### Prometheus backend

```python
from lexigram.monitor.config import MonitorConfig, BackendType

config = MonitorConfig(backend_type=BackendType.PROMETHEUS)
```

- Exposes a `/metrics` endpoint on `PrometheusConfig.port` (default `9090`).
- Supports Pushgateway for batch job metrics via `pushgateway_url`.
- Can persist samples to a database table (`store_in_db`, `metrics_table`).

### OpenTelemetry backend

```python
config = MonitorConfig(backend_type=BackendType.OPENTELEMETRY)
```

- Exports via OTLP to a collector (`OpenTelemetryConfig.endpoint`).
- Supports configurable batch size, export interval, and compression.
- Tracing and metrics exporters are independently configurable via `TracingExporterRegistry` and `MetricsExporterRegistry`.

### Memory backend

Default for development. Metrics stay in-process. `InMemoryTraceProvider` stores spans up to `TracingConfig.max_spans`.

## Custom metric creation

```python
from lexigram.monitor.metrics import Counter

counter = collector.create_counter(
    "payment_attempts_total",
    "Total payment processing attempts",
    labels={"provider": "", "status": ""},
)
counter.increment(labels={"provider": "stripe", "status": "success"})
```

Or via `MonitorProvider` helpers:

```python
monitor = await container.resolve(MonitorProvider)
monitor.create_gauge("queue_depth", "Current queue depth")
```

## Health check patterns

Health checks are registered via `HealthCheckerRegistry`:

```python
from lexigram.monitor.health import HealthCheckerRegistry, health_checker

registry = await container.resolve(HealthCheckerRegistry)

@health_checker("database", registry)
async def check_db() -> HealthCheckResult:
    if await db.ping():
        return HealthCheckResult(component="db", status=HealthStatus.HEALTHY)
    return HealthCheckResult(component="db", status=HealthStatus.UNHEALTHY)
```

Built-in checks aggregate via `HealthCheckRegistry`:

```python
from lexigram.monitor.health import HealthCheckRegistry

check_registry = await container.resolve(HealthCheckRegistry)
results = await check_registry.run_checks(timeout=5.0)
```

## Tracing span attributes

Spans created by the monitor carry standard attributes:

```python
from lexigram.monitor.tracing import SpanKind, SpanStatus

span = tracer.start_span(
    "payment.charge",
    attributes={
        "payment.provider": "stripe",
        "payment.amount": 5000,
        "payment.currency": "USD",
    },
    kind=SpanKind.CLIENT,
)
# ... work ...
span.set_status(SpanStatus.OK)
span.end()
```

Decorator-based tracing via `@traced`:

```python
from lexigram.monitor.instrumentation.decorators import traced

@traced("payment_service")
async def charge(amount: int) -> None:
    ...
```

## See also

- `MonitorConfig` — backend type, metrics, tracing, and health config
- `MetricsCollectorProtocol` — create and manage metrics
- `Counter`, `Gauge`, `Histogram`, `Summary` — metric implementations
- `MonitorProvider` — DI registration and default metrics
- `HealthCheckConfig` — health check endpoint and timeout settings
