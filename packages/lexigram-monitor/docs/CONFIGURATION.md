---
title: lexigram-monitor Configuration
description: All configuration keys for the monitoring subsystem.
---

Config section: `monitor` (`MonitorConfig`). Env prefix: `LEX_MONITOR__`.

## Root Options

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `enabled` | `bool` | `True` | `LEX_MONITOR__ENABLED` | Enable monitoring |
| `name` | `str` | `"lexigram-service"` | `LEX_MONITOR__NAME` | Service name / provider name |
| `backend_type` | `BackendType` | `memory` | `LEX_MONITOR__BACKEND_TYPE` | Monitoring backend (opentelemetry / prometheus / memory) |
| `environment` | `Environment` | `development` | — | Deployment environment |
| `env` | `str \| None` | `None` | `LEX_MONITOR__ENV` | Environment override string |
| `debug` | `bool` | `False` | `LEX_MONITOR__DEBUG` | Enable debug mode |

## Metrics (`metrics:`)

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `metrics.enabled` | `bool` | `True` | `LEX_MONITOR__METRICS__ENABLED` | Enable metrics collection |
| `metrics.prefix` | `str` | `"lexigram_"` | `LEX_MONITOR__METRICS__PREFIX` | Metric name prefix |
| `metrics.default_labels` | `dict[str, str]` | `{}` | — | Default labels for all metrics |
| `metrics.histogram_buckets` | `list[float]` | `[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]` | — | Default histogram bucket boundaries |
| `metrics.collection_interval` | `float` | `60.0` | `LEX_MONITOR__METRICS__COLLECTION_INTERVAL` | Metrics collection interval (seconds) |

## Tracing (`tracing:`)

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `tracing.enabled` | `bool` | `True` | `LEX_MONITOR__TRACING__ENABLED` | Enable tracing |
| `tracing.service_name` | `str` | `"lexigram-service"` | `LEX_MONITOR__TRACING__SERVICE_NAME` | Service name for traces |
| `tracing.sampler_type` | `SamplerType` | `always_on` | `LEX_MONITOR__TRACING__SAMPLER_TYPE` | Sampling strategy |
| `tracing.sample_rate` | `float` | `1.0` | `LEX_MONITOR__TRACING__SAMPLE_RATE` | Sample rate (0.0–1.0) |
| `tracing.max_traces_per_second` | `int` | `100` | — | Rate limit for rate_limiting sampler |
| `tracing.propagation_formats` | `list[str]` | `["tracecontext", "baggage"]` | — | Trace propagation formats |
| `tracing.max_attributes` | `int` | `128` | — | Max attributes per span |
| `tracing.max_events` | `int` | `128` | — | Max events per span |
| `tracing.max_links` | `int` | `128` | — | Max links per span |
| `tracing.max_spans` | `int` | `1000` | — | Max in-memory spans |

## Health Checks (`health:`)

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `health.enabled` | `bool` | `True` | `LEX_MONITOR__HEALTH__ENABLED` | Enable health checks |
| `health.path` | `str` | `"/health"` | `LEX_MONITOR__HEALTH__PATH` | Health endpoint path |
| `health.include_details` | `bool` | `True` | — | Include detailed health info |
| `health.timeout` | `float` | `5.0` | `LEX_MONITOR__HEALTH__TIMEOUT` | Health check timeout (seconds) |
| `health.checks` | `list[str]` | `[]` | — | Health check names to run |
| `health.interval` | `int` | `30` | `LEX_MONITOR__HEALTH__INTERVAL` | Health check interval (seconds) |

## Logging

Structured logging is owned by `lexigram.core` and configured through the core `logging` section (`LEX_LEXIGRAM__LOGGING__*`), not `MonitorConfig`. When the monitor package is used with core, use `LEX_LEXIGRAM__LOGGING__*` to set log level, format, redaction, sampling, and per-logger levels. See the core logging configuration documentation for the full key list.

## OpenTelemetry (`opentelemetry:`)

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `opentelemetry.endpoint` | `str \| None` | `None` | `LEX_MONITOR__OPENTELEMETRY__ENDPOINT` | OTLP endpoint URL |
| `opentelemetry.headers` | `dict[str, str]` | `{}` | — | OTLP request headers |
| `opentelemetry.insecure` | `bool` | `False` | — | Use insecure connection |
| `opentelemetry.timeout` | `float` | `30.0` | — | Export timeout (seconds) |
| `opentelemetry.compression` | `str` | `"none"` | — | Compression (none / gzip) |
| `opentelemetry.batch_size` | `int` | `512` | — | Export batch size |
| `opentelemetry.export_interval` | `float` | `5.0` | — | Export interval (seconds) |
| `opentelemetry.tracing_exporters` | `list[OTelExporterConfig]` | `[{"type":"console"}]` | — | Tracing exporter configs |
| `opentelemetry.metrics_exporters` | `list[OTelExporterConfig]` | `[{"type":"console"}]` | — | Metrics exporter configs |

## Prometheus (`prometheus:`)

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `prometheus.port` | `int` | `8000` | `LEX_MONITOR__PROMETHEUS__PORT` | Metrics server port |
| `prometheus.path` | `str` | `"/metrics"` | `LEX_MONITOR__PROMETHEUS__PATH` | Metrics endpoint path |
| `prometheus.enable_default_metrics` | `bool` | `True` | — | Enable default process metrics |
| `prometheus.pushgateway_url` | `str \| None` | `None` | — | Pushgateway URL |
| `prometheus.push_interval` | `float` | `10.0` | — | Pushgateway push interval |
| `prometheus.store_in_db` | `bool` | `False` | — | Persist metrics to database |
| `prometheus.metrics_table` | `str` | `"metrics_samples"` | — | DB metrics table name |

## YAML Example

```yaml
monitor:
  backend_type: prometheus
  environment: production
  metrics:
    enabled: true
    prefix: myapp_
    histogram_buckets: [0.05, 0.1, 0.5, 1.0, 5.0]
  tracing:
    enabled: true
    service_name: my-service
    sampler_type: probability
    sample_rate: 0.1
  health:
    path: /health
    include_details: true
  prometheus:
    port: 8000
    path: /metrics
```

## Env-Only Example

```bash
export LEX_MONITOR__BACKEND_TYPE=prometheus
export LEX_MONITOR__TRACING__ENABLED=true
export LEX_MONITOR__TRACING__SAMPLE_RATE=0.1
export LEX_MONITOR__PROMETHEUS__PORT=8000
```
