---
title: lexigram-resilience Guide
description: Concepts, mental model, and common usage patterns for lexigram-resilience
sidebar:
  order: 2
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |

## Problem

External calls (APIs, databases, services) fail intermittently, slow down, or go down entirely. Without protection, a single failing dependency cascades — consuming threads, exhausting connections, and degrading your entire application.

**lexigram-resilience** provides proven fault-tolerance patterns to make your application resilient to failure.

## Mental Model

Each pattern addresses a specific failure mode:

| Pattern | Failure Mode | Effect |
|---------|-------------|--------|
| Circuit Breaker | Cascading failures | Stops calls when a service is down. Throws `CircuitOpenError`. |
| Retry | Transient errors | Re-executes with exponential backoff and jitter. |
| Bulkhead | Resource exhaustion | Isolates calls into semaphore-guarded pools. |
| Timeout | Slow responses | Cancels operations that exceed a budget. Throws `ResilienceTimeoutError`. |
| Rate Limiter | Overload | Limits request rate with a token-bucket algorithm. |
| Throttle | Burst traffic | Smooths request flow over a sliding window. |

Patterns compose via `ResiliencePipeline`. You can wire the pipeline through DI to avoid hardcoding any resilience logic in your services.

## Core Concepts

### Circuit Breaker

Tracks failures per named breaker. When the `failure_threshold` is reached the circuit **opens** — subsequent calls fail fast. After `recovery_timeout` seconds the circuit transitions to **half-open** for a single probe call. Success closes it; failure keeps it open.

```python
from lexigram.resilience import CircuitBreaker, CircuitBreakerConfig
from lexigram.resilience.circuit import CircuitState

config = CircuitBreakerConfig(failure_threshold=5, recovery_timeout=30.0)
breaker = CircuitBreaker(config)

async with breaker.protect():
    result = await risky_api_call()

# Or use the decorator with a registry:
from lexigram.resilience import circuit_breaker, CircuitBreakerRegistry

registry = CircuitBreakerRegistry()

@circuit_breaker("api", registry)
async def call_api() -> dict:
    ...
```

### Retry

Re-executes with configurable backoff. Retryable exceptions are specified via `retry_on`; `abort_on` excludes non-retryable errors. Jitter prevents thundering herds.

```python
from lexigram.resilience import retry, RetryConfig
from lexigram.contracts.exceptions import DomainError

cfg = RetryConfig(max_attempts=3, base_delay=1.0, jitter=True)

@retry(cfg)
async def fetch_payment(id: str) -> dict:
    ...
```

Use `abort_on` to skip retries for non-retryable errors:

```python
cfg = RetryConfig(
    max_attempts=3,
    abort_on=(ValueError, PermissionError),
)
```

### Bulkhead

Limits concurrency with a semaphore. When `max_concurrent` is exceeded, calls queue (up to `queue_size`) or are rejected.

```python
from lexigram.resilience import bulkhead, BulkheadConfig

@bulkhead(BulkheadConfig(max_concurrent=5, queue_size=50))
async def db_query(query: str) -> list[dict]:
    ...
```

### Timeout

Cancels operations exceeding a duration. Powered by `asyncio.timeout`.

```python
from lexigram.resilience import with_timeout, TimeoutConfig

@with_timeout(TimeoutConfig(timeout=5.0))
async def fetch_data() -> dict:
    ...
```

### ResiliencePipeline

Combines multiple patterns in a configurable order. Default order: bulkhead → circuit breaker → retry → timeout.

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
result = await pipeline.execute(my_function, arg1, arg2)
```

Accept `ResiliencePipelineFactoryProtocol | None` in your service constructors for testable resilience:

```python
from lexigram.contracts.infra.resilience import ResiliencePipelineFactoryProtocol

class PaymentService:
    def __init__(self, pipeline_factory: ResiliencePipelineFactoryProtocol | None = None) -> None:
        self._factory = pipeline_factory
```

### Rate Limiting

Token-bucket rate limiter that blocks until a token is available:

```python
from lexigram.resilience import RateLimiter

limiter = RateLimiter(rate=100)  # 100 tokens/sec

async def handle_request() -> None:
    await limiter.acquire()
    ...
```

### Throttle

Sliding-window throttler with configurable call count per period:

```python
from lexigram.resilience import Throttler

throttler = Throttler(calls=100, period=60.0)

async def api_handler() -> dict:
    ...
```

### Idempotency

Guarantees at-most-once execution. Results are cached in a pluggable store (in-memory, Redis, SQL).

```python
from lexigram.resilience import idempotent, InMemoryIdempotencyStore

store = InMemoryIdempotencyStore()

@idempotent(store, ttl=3600.0)
async def create_order(order_id: str) -> dict:
    ...
```

## Best Practices

- **Circuit breaker every downstream.** Protect each outbound HTTP call, database query, and queue publish with a named breaker.
- **Retry transient failures only.** Use `abort_on=()` to exclude auth and validation errors from retry.
- **Bulkhead resource pools.** Isolate database connections from API calls so a slow API does not starve the database.
- **Set timeouts everywhere.** An unbounded timeout is an unlimited resource leak.
- **Wire via DI.** Accept `ResiliencePipelineFactoryProtocol | None` in constructors — test mocks can disable resilience.

## Next Steps

- [Architecture](./ARCHITECTURE.md) — internals and extension points
- [Configuration](./CONFIGURATION.md) — all config fields with defaults
- [How-Tos](./HOWTOS.md) — recipes for common scenarios
