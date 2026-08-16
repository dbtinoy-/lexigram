---
title: lexigram-resilience Quickstart
description: Get started with lexigram-resilience — circuit breakers, retries, bulkheads, and more
sidebar:
  order: 1
---

Install, wire, and use resilience patterns in under 5 minutes.

## Install

```bash
uv add lexigram-resilience
```

## Minimal Wiring

```python
import asyncio
from lexigram import Application
from lexigram.resilience import ResilienceProvider
from lexigram.resilience.config import ResilienceConfig

config = ResilienceConfig()
provider = ResilienceProvider()

async def main() -> None:
    async with Application.boot(
        name="demo",
        providers=[provider],
        config=config,
    ) as app:
        print("Resilience provider ready")

asyncio.run(main())
```

## Use a Decorator

```python
from lexigram.resilience import retry, RetryConfig
from lexigram.resilience import circuit_breaker, CircuitBreakerRegistry

cfg = RetryConfig(max_attempts=3, base_delay=1.0)
registry = CircuitBreakerRegistry()

@retry(cfg)
async def fetch_data(url: str) -> dict:
    ...

@circuit_breaker("api", registry)
async def call_external() -> dict:
    ...
```

## Use the Pipeline

```python
from lexigram.resilience import ResiliencePipeline
from lexigram.contracts.infra.resilience import RetryConfig, CircuitBreakerConfig

pipeline = ResiliencePipeline(
    retry_config=RetryConfig(max_attempts=3),
    circuit_config=CircuitBreakerConfig(failure_threshold=5),
)
result = await pipeline.execute(my_function, arg1, arg2)
```

## Next Steps

- [Guide](./GUIDE.md) — concepts and mental model
- [Configuration](./CONFIGURATION.md) — all config fields
- [How-Tos](./HOWTOS.md) — common recipes
