---
title: lexigram-monitor Troubleshooting
description: Common errors, causes, and fixes.
---

## Backend not available

**Error:** `BackendNotAvailableError` (code `LEX_ERR_MONITOR_002`)

**Cause:** The configured monitoring backend requires an optional dependency that is not installed.

**Fix:** Install the required extra:

```bash
# For Prometheus
uv add "lexigram-monitor[prometheus]"
# For OpenTelemetry
uv add "lexigram-monitor[otel]"
# For system metrics
uv add "lexigram-monitor[system]"
```

## Metric not found

**Error:** `MetricNotFoundError` (code `LEX_ERR_MONITOR_003`)

**Cause:** Attempting to access a metric that hasn't been created yet.

**Fix:** Create the metric before accessing it:

```python
from lexigram.monitor import Counter

provider = await container.resolve(MonitorProvider)

# Create first
counter = provider.create_counter("my_metric", "My metric")

# Then access
metric = provider.metrics_collector.get_metric("my_metric")
if metric is not None:
    metric.increment()
```

## Invalid metric parameters

**Error:** `InvalidMetricError` (code `LEX_ERR_MONITOR_004`)

**Cause:** Metric creation failed — invalid name, negative bucket boundaries, or reserved label names.

**Fix:** Verify metric name follows the prefix naming convention and label values are valid strings:

```python
# Metric names must not be empty
counter = provider.create_counter("", "desc")  # raises InvalidMetricError

# Histogram buckets must be positive
histogram = provider.create_histogram("latency", "Latency", buckets=[-1, 0])  # raises InvalidMetricError
```

## Span not found

**Error:** `SpanNotFoundError` (code `LEX_ERR_MONITOR_006`)

**Cause:** Trying to access a span that was never created or has already been flushed.

**Fix:** Check span existence before access:

```python
tracer = await container.resolve(TracerProtocol)
spans = tracer.get_all_spans()
if len(spans) > 0:
    first_span = spans[0]
```

## Prometheus port conflict

**Error:** `OSError: [Errno 48] Address already in use` (or `OSError: [Errno 98]` on Linux)

**Cause:** The Prometheus metrics server port is already in use by another process.

**Fix:** Change the port in config:

```yaml
monitor:
  prometheus:
    port: 8001  # change from default 8000
```

## No metrics appearing at /metrics endpoint

**Cause 1:** `PrometheusMiddleware` is not wrapped around your web ASGI app:

```python
from lexigram.monitor.middleware import PrometheusMiddleware

# Wrap the web ASGI app:
web_app = await container.resolve(WebProvider).get_app()
app = PrometheusMiddleware(web_app, path="/metrics")
```

**Cause 2:** No metrics have been created or incremented yet. Verify by calling `provider.metrics_collector.get_all_metrics()`.

**Cause 3:** The Prometheus backend is not configured. Ensure `backend_type: prometheus` is set in config.

## Tracing spans not exported

**Cause:** The OpenTelemetry exporter is misconfigured or unreachable.

**Fix:** Check the OTLP endpoint URL and network connectivity:

```bash
# Verify the collector is reachable
curl -v http://otel-collector:4318/v1/traces

# Enable debug logging
export LEX_MONITOR__DEBUG=true
```

For development, use the console exporter:

```yaml
monitor:
  opentelemetry:
    tracing_exporters:
      - type: console
```

## Health check always returns UNKNOWN

**Cause:** No health checks have been registered with `HealthCheckRegistry`.

**Fix:** Register at least one health check:

```python
from lexigram.monitor.health import (
    HealthCheckRegistry,
    FunctionHealthCheck,
)

registry = await container.resolve(HealthCheckRegistry)
registry.register("app", FunctionHealthCheck(check_fn=lambda: True))
```

## SLO compliance is 0%

**Cause:** `SLOMonitor` has no observations recorded for the SLO window.

**Fix:** Call `slo_monitor.record_observation(success=True)` for each operation being measured.
