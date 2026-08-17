---
title: lexigram-ai-observability Troubleshooting
description: Common errors, causes, and fixes for AI observability.
---

## `MetricsError` — Metrics recording failed

**Exception:** `lexigram.ai.observability.exceptions.MetricsError`

**Cause:** The `MetricsCollectorProtocol` backend is unavailable or raised an error during `increment()` / `observe()`.

**Fix:** Verify `lexigram-monitor` or your custom `MetricsCollectorProtocol` implementation is registered and its backend (Prometheus, StatsD) is reachable. Check the collector's `initialize()` completed without errors.

## `TracingError` — Trace span creation failed

**Exception:** `lexigram.ai.observability.exceptions.TracingError`

**Cause:** The `TracerProtocol` backend (e.g. OpenTelemetry) is not initialized or the exporter endpoint is unreachable.

**Fix:** Ensure a `TracerProtocol` implementation is registered in the container before `ObservabilityProvider.boot()`. If using OpenTelemetry, confirm the `OTLPSpanExporter` endpoint is correct.

## `HealthCheckError` — Health check infrastructure operation failed

**Exception:** `lexigram.ai.observability.exceptions.HealthCheckError`

**Cause:** Internal error in the health check system itself (not a component being unhealthy).

**Fix:** Check the exception details — this indicates a bug in the health check registration or execution code. Ensure all registered check callables are async and handle their own errors gracefully.

## LLM calls are not traced

**Symptom:** No spans appear in the trace backend. LLM completions work normally.

**Cause:** `LLMClientProtocol` was registered after `ObservabilityProvider.boot()` ran, or the provider's `enabled` flag is `false`.

**Fix:**

```python
# Ensure correct wiring order
app = Application(name="my-app")
app.add_module(LLMModule.configure())
app.add_module(ObservabilityModule.configure())
await app.start()
```

Check `observability_enabled` in your config:

```yaml
ai_observability:
  enabled: true
```

## Metrics are not appearing

**Symptom:** Prometheus or your metrics backend shows no `intelligence_*` metrics.

**Cause 1:** `metrics_enabled` is `false`.

```yaml
ai_observability:
  metrics_enabled: true  # must be true
```

**Cause 2:** `AIMetrics` requires a `MetricsCollectorProtocol` — if `lexigram-monitor` is not installed or its provider didn't register the collector, `AIMetrics` raises a `ValueError`.

**Fix:** Install and wire `lexigram-monitor`:

```bash
uv add lexigram-monitor
```

## Container resolution fails with `ObservabilityProvider`

**Symptom:** `ValueError` or `KeyError` during `boot()`.

**Cause:** The provider tries to gracefully handle missing `AITracer`/`AIMetrics` — it logs a debug message and skips wrapping.

**Fix:** This is not an error. Check `debug`-level logs for `observability_tracer_metrics_unavailable` or `observability_no_llm_to_wrap`. If you expect tracing/metrics, ensure `AITracer` and `AIMetrics` are registered (they are, if `enabled` is `true` — the provider registers them itself).

## Wrapped LLM client not capturing traces

**Symptom:** LLM calls work normally but no trace spans appear in the backend.

**Cause:** `ObservabilityProvider.boot()` runs before the LLM client is registered in the container. The provider only wraps clients that exist at boot time — if an LLM sub-provider registers its client after the observability provider boots, wrapping is skipped.

**Fix:** Ensure the LLM provider is registered *before* the observability provider:

```python
app.add_module(LLMModule.configure(config))
app.add_module(ObservabilityModule.configure())  # must come after LLM
```

Check boot-time logs for `observability_llm_wrapped` (success) vs `observability_no_llm_to_wrap` (skipped).

## `HealthCheckError` during health check registration

```python
HealthCheckError: Failed to register health check 'vector_store'
```

**Cause:** The health check callable raised an exception during registration. Health checks must be async functions or callables that accept no required arguments.

**Fix:** Wrap the health check logic to handle errors internally:

```python
from lexigram.ai.observability.health import AIHealthMonitor

monitor = await container.resolve(AIHealthMonitor)
await monitor.register_check("vector_store", check_fn=lambda: store_health_check())
```

Ensure all registered checks return a `HealthCheckResult` or a boolean.

## Metrics recording not reflected in backend

**Symptom:** `AIMetrics.increment()` returns successfully but no data appears in Prometheus or StatsD.

**Cause:** The `MetricsCollectorProtocol` backend wasn't initialized or was registered after `AIMetrics` was created. `AIMetrics` holds a reference to the collector at construction time — late-registered collectors are not used.

**Fix:** Ensure `MetricsCollectorProtocol` is registered before `AIMetrics` is resolved:

```python
# Register the collector first
container.singleton(MetricsCollectorProtocol, PrometheusCollector())

# Then AIMetrics picks it up automatically
metrics = await container.resolve(AIMetrics)
```

Verify the collector's `initialize()` method completed without errors.

## Tracing context lost across async boundaries

**Symptom:** Trace spans appear disconnected — parent-child relationships are missing.

**Cause:** The `AITracer` uses `contextvars` to propagate the active span. When work is dispatched to a thread pool or a new `asyncio.Task` created with `asyncio.create_task()`, the context variable is not automatically propagated.

**Fix:** Use the framework's tracked task helper to preserve tracing context:

```python
from lexigram.concurrency.task_utils import create_tracked_task

# Instead of asyncio.create_task()
task = await create_tracked_task(self._process_job(job))
```
