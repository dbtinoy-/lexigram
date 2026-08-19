---
title: lexigram-resilience How-Tos
description: Common recipes for lexigram-resilience
sidebar:
  order: 5
---

## Protect an HTTP Client with Circuit Breaker + Retry

```python
from lexigram.resilience import CircuitBreakerRegistry, RetryConfig
from lexigram.resilience.decorators import circuit_breaker, retry

registry = CircuitBreakerRegistry()
cfg = RetryConfig(max_attempts=3, base_delay=0.5)

@retry(cfg)
@circuit_breaker("external_api", registry)
async def call_api(url: str) -> dict:
    ...
```

## Isolate Database Connections with Bulkhead

```python
from lexigram.resilience import bulkhead, BulkheadConfig

@bulkhead(BulkheadConfig(max_concurrent=10, queue_size=50))
async def run_query(sql: str) -> list[dict]:
    ...
```

## Set a Timeout on an External Call

```python
from lexigram.resilience import with_timeout, TimeoutConfig

@with_timeout(TimeoutConfig(timeout=5.0))
async def fetch_price(symbol: str) -> float:
    ...
```

## Combine Patterns in a Pipeline

```python
from lexigram.resilience import ResiliencePipeline
from lexigram.contracts.infra.resilience import (
    RetryConfig, CircuitBreakerConfig, TimeoutConfig,
)

pipeline = ResiliencePipeline(
    retry_config=RetryConfig(max_attempts=3),
    circuit_config=CircuitBreakerConfig(failure_threshold=5),
    timeout_config=TimeoutConfig(timeout=10.0),
    order=["circuit_breaker", "retry", "timeout"],  # no bulkhead
)
result = await pipeline.execute(expensive_operation, arg1)
```

## Rate-Limit an API Handler

```python
from lexigram.resilience import RateLimiter

limiter = RateLimiter(rate=50)  # 50 tokens/second

async def handler(request: dict) -> dict:
    await limiter.acquire()
    ...
```

## Throttle a Traffic Spike

```python
from lexigram.resilience import Throttler

throttler = Throttler(calls=200, period=60.0)

async def webhook_handler(payload: dict) -> dict:
    ...
```

## Ensure Idempotent Order Creation

```python
from lexigram.resilience import idempotent, InMemoryIdempotencyStore

store = InMemoryIdempotencyStore()

@idempotent(store, ttl=86400.0)
async def create_order(order_id: str, amount: float) -> dict:
    """Creates an order at most once per order_id."""
    return {"id": order_id, "amount": amount}
```

## Wire Resilience via Module

```python
from lexigram import Application
from lexigram.resilience import ResilienceModule

app = Application(name="my-app")
app.add_module(ResilienceModule.configure())
```
