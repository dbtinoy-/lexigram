---
title: lexigram-monitor Quickstart
description: Install, wire monitoring, and collect your first metrics.
---

:::note[Maturity]
`lexigram-monitor` is **alpha (0.1.x)** and MIT-licensed. Public APIs may change before 1.0.
:::

## Install

```bash
uv add lexigram-monitor
```

For production monitoring, install your backend extra:

```bash
# Prometheus metrics
uv add "lexigram-monitor[prometheus]"
# OpenTelemetry tracing (OTLP)
uv add "lexigram-monitor[otel]"
# System metrics (CPU, memory)
uv add "lexigram-monitor[system]"
# All extras
uv add "lexigram-monitor[all]"
```

## Minimal Example

```python
import asyncio

from lexigram import Application, LexigramConfig
from lexigram.monitor import MonitorProvider
from lexigram.observability.core import NoOpMetricsBackend


async def main():
    config = LexigramConfig.from_yaml("application.yaml")
    app = Application(name="my-app", config=config)
    app.add_provider(MonitorProvider(backend=NoOpMetricsBackend()))

    async with app.boot():
        # Create and increment a counter
        provider = await app.container.resolve(MonitorProvider)
        counter = provider.create_counter("requests_total", "Total requests")
        counter.increment()
        counter.increment(5)
        print(f"Count: {counter.get_count()}")

        # Record an HTTP request
        provider.record_request("GET", "/api/users", 0.125, 200)

        # Read health
        health = await provider.health_check()
        print(f"Status: {health.status}")


asyncio.run(main())
```

## Wiring

Add `MonitorProvider` to your `Application`. The provider auto-discovers `MonitorConfig` from the `monitor:` section of your YAML config:

```python
from lexigram.monitor import MonitorProvider
from lexigram.monitor.config import MonitorConfig

# In-memory (development / testing)
app.add_provider(MonitorProvider(backend=NoOpMetricsBackend()))

# From config — reads LEX_MONITOR__* env vars
provider = MonitorProvider.from_config(MonitorConfig())
app.add_provider(provider)
```

Or use the declarative `MonitorModule`:

```python
from lexigram.monitor import MonitorModule
from lexigram.monitor.backends.prometheus import PrometheusBackend

app.add_module(MonitorModule.configure(backend=PrometheusBackend()))
```

## What Just Happened

- `MonitorProvider` registered singletons for `MetricsCollectorProtocol`, `TracerProtocol`, and `HealthCheckRegistryProtocol`
- The `@traced` and `@metered` decorators now resolve real implementations from the container
- `health_check()` returns component status with backend type and metric count

## Next Steps

- [Guide](./GUIDE.md) — mental model, core concepts, best practices
- [Configuration](./CONFIGURATION.md) — every config key with defaults and env vars
- [How-Tos](./HOWTOS.md) — common recipes
