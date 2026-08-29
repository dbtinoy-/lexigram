---
title: lexigram-monitor Guide
description: Mental model, core concepts, and end-to-end usage of observability.
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `lexigram-notification` | Optional | Alerting integration |

## Problem

Your application needs health checks, metrics, distributed tracing, and structured logging. Wiring each observability concern by hand is brittle and couples your code to specific vendors (Prometheus, Datadog, Grafana).

`lexigram-monitor` provides a unified observability layer behind protocols. Swap backends (Memory → Prometheus → OpenTelemetry) without changing application code.

## Mental Model

```
Application Code
        │
        ▼
 ┌────────────────────────────────┐
 │ lexigram-monitor (MonitorProvider) │
 │  ┌──────────┐ ┌───────┐ ┌────┐ │
 │  │ Metrics   │ │ Trace │ │Health│ │
 │  │ Counter   │ │ Span  │ │Check │ │
 │  │ Gauge     │ │ Tracer│ │      │ │
 │  │ Histogram │ │       │ │      │ │
 │  └────┬─────┘ └───┬───┘ └──┬───┘ │
 └───────┼───────────┼────────┼─────┘
         │           │        │
    ┌────▼────┐ ┌───▼───┐ ┌──▼────┐
    │Prometheus│ │  OTel  │ │Memory │
    │ Backend  │ │Backend │ │Backend│
    └─────────┘ └───────┘ └───────┘
```

Every concern is a contract. The backend provides the implementation.

## Core Concepts

### Metrics

Four metric types, all created through `MetricsCollectorProtocol`:

```python
from lexigram.monitor import Counter, Gauge, Histogram, Summary

# Counter — cumulative count that only increases
counter = collector.create_counter("requests_total", "Total requests")
counter.increment()
counter.increment(5)

# Gauge — value that goes up and down
gauge = collector.create_gauge("active_connections", "Active connections")
gauge.set(10.5)
gauge.increment(2.0)
gauge.decrement(1.0)

# Histogram — distribution of values
histogram = collector.create_histogram("request_duration_ms", "Request latencies")
histogram.observe(0.125)
histogram.observe(0.500)
```

### Tracing

Distributed tracing via `TracerProtocol`:

```python
from lexigram.monitor import Tracer, SpanKind, SpanStatus

with tracer.start_span("process_order") as span:
    span.set_attribute("order_id", "ord-42")
    span.set_attribute("user_id", "usr-7")
    span.add_event("payment_processed")
    # ... do work
    span.set_status(SpanStatus.OK)
```

### Health Checks

Register component health checks via `HealthCheckRegistry`:

```python
from lexigram.monitor.health import HealthCheckRegistry, HealthCheck

class DatabaseHealthCheck(HealthCheck):
    async def check(self, timeout: float = 5.0) -> HealthCheckResult:
        try:
            await self.db.execute("SELECT 1")
            return HealthCheckResult(component="db", status=HealthStatus.HEALTHY)
        except ConnectionError as e:
            return HealthCheckResult(component="db", status=HealthStatus.UNHEALTHY, error=str(e))

registry = await container.resolve(HealthCheckRegistry)
registry.register("database", DatabaseHealthCheck(db=...))
```

### Decorators

Use `@traced` and `@metered` to instrument functions declaratively:

```python
from lexigram.monitor import traced, metered

@traced("process_order")
@metered("orders_processed")
async def process_order(order_id: str) -> None:
    ...
```

### Hook Subscriptions

`MonitorProvider` optionally subscribes to framework hooks to emit metrics automatically for cache, events, SQL, web, auth, queue, and task operations. Enable by registering any provider that exposes a `HookRegistryProtocol`.

## Typical Usage

### Prometheus metrics with a web endpoint

```python
from lexigram.monitor import MonitorProvider
from lexigram.monitor.backends.prometheus import PrometheusBackend
from lexigram.monitor.middleware import PrometheusMiddleware

# Wrap the ASGI app with Prometheus middleware to serve /metrics
backend = PrometheusBackend(port=8000, path="/metrics")
app.add_provider(MonitorProvider(backend=backend))

# At the ASGI server level, wrap your web app:
web_app = container.resolve(WebProvider).app
app = PrometheusMiddleware(web_app, path="/metrics")
# Optional: auth_token="..." likewise requires Authorization: Bearer on /metrics
```

### OpenTelemetry tracing

```python
from lexigram.monitor import MonitorProvider
from lexigram.monitor.backends.opentelemetry import OpenTelemetryBackend

backend = OpenTelemetryBackend(
    endpoint="http://otel-collector:4318",
    service_name="my-service",
)
app.add_provider(MonitorProvider(backend=backend))
```

### Health check endpoint

```python
from lexigram.monitor.middleware import HealthCheckProvider

# Optional: require `Authorization: Bearer <token>` on the endpoint.
# Omit `auth_token` (the default) to keep the endpoint open for k8s probes.
app.add_provider(HealthCheckProvider(path="/health", auth_token=os.environ.get("HEALTH_TOKEN")))
```

## Common Patterns

### Profiling

```python
from lexigram.monitor import PerformanceMonitor

monitor = PerformanceMonitor()
with monitor.track("expensive_op") as ctx:
    result = await do_expensive_work()
print(f"Took {ctx.duration_ms}ms")
```

### SLO monitoring

```python
from lexigram.monitor.slo import SLO, SLOMonitor

slo = SLO(name="api_latency", target=99.0, window_seconds=3600)
slo_monitor = SLOMonitor(slos=[slo])
slo_monitor.record_observation(0.125)  # 125ms
```

## Best Practices

- Use `NoOpMetricsBackend` in tests to avoid side effects from metric recording
- Prefer `@traced` and `@metered` decorators over manual span/metric calls
- Register health checks for every external dependency (database, cache, search, etc.)
- Configure core logging redaction via `LEX_LEXIGRAM__LOGGING__REDACTION__*` (not `MonitorConfig`) to prevent secrets from appearing in logs
- Use `PrometheusMiddleware` for pull-based metrics; use `Pushgateway` for batch jobs
- Set `tracing.sampler_type` to `probability` with `sample_rate: 0.1` in high-traffic production
