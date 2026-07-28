---
title: lexigram-ai-observability Configuration
description: All config keys, types, defaults, and environment variables.
---

## Config Key

The configuration section is `ai_observability` (loaded from the `ai_observability:` key in `application.yaml`).

## Options

| Key | Type | Default | Env Variable | Description |
|-----|------|---------|-------------|-------------|
| `enabled` | `bool` | `true` | `LEX_AI_OBSERVABILITY__ENABLED` | Master on/off switch for all AI observability |
| `metrics_enabled` | `bool` | `true` | `LEX_AI_OBSERVABILITY__METRICS_ENABLED` | Enable metrics collection (counters, histograms, gauges) |
| `tracing_enabled` | `bool` | `true` | `LEX_AI_OBSERVABILITY__TRACING_ENABLED` | Enable distributed tracing (span creation and export) |
| `health_checks_enabled` | `bool` | `true` | `LEX_AI_OBSERVABILITY__HEALTH_CHECKS_ENABLED` | Enable background health checking for AI components |

## Example YAML

```yaml
ai_observability:
  enabled: true
  metrics_enabled: true
  tracing_enabled: true
  health_checks_enabled: true
```

## Minimal (production-hardened) YAML

```yaml
ai_observability:
  enabled: true
  metrics_enabled: true
  tracing_enabled: true
  health_checks_enabled: true
```

## Env Variable Override

```bash
export LEX_AI_OBSERVABILITY__ENABLED=true
export LEX_AI_OBSERVABILITY__TRACING_ENABLED=true
export LEX_AI_OBSERVABILITY__METRICS_ENABLED=false
```

## Production Warnings

When `Environment.PRODUCTION` is detected, the config's `validate_for_environment()` method emits warnings if `tracing_enabled` or `metrics_enabled` are `false` — these features are expected in production for operational visibility.

## Programmatic

```python
from lexigram.ai.observability.config import ObservabilityConfig

config = ObservabilityConfig(
    enabled=True,
    metrics_enabled=True,
    tracing_enabled=False,
    health_checks_enabled=True,
)
```

## Config Model

Loaded as a `BaseConfig` subclass (`ObservabilityConfig`) by `ObservabilityProvider`. The config instance is registered as a container singleton at `register()` time and can be resolved by other services:

```python
cfg = await container.resolve(ObservabilityConfig)
```
