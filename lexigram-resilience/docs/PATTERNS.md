---
title: lexigram-resilience Patterns
description: Circuit breaker, retry, bulkhead, rate limiter, timeout, throttle, fallback — when and how to use each.
---

> **Alpha (0.1.x)** — MIT licensed. Public API may change before 1.0.

## Circuit breaker

**What it is:** Stops calls to a failing dependency when failures reach a threshold. After a recovery timeout, a single probe call tests if the service is back. Prevents cascading failures.

**Config (`CircuitBreakerConfig`):**

```python
from lexigram.contracts.infra.resilience.models import CircuitBreakerConfig

CircuitBreakerConfig(
    failure_threshold=5,        # Failures before opening
    recovery_timeout=30.0,      # Seconds before half-open probe
    half_open_max_calls=1,      # Probe calls in half-open state
    success_threshold=2,        # Successes before closing
)
```

**When to use:** Calls to external APIs, databases, or any service with a risk of downtime.

**When NOT to use:** Local in-memory operations, idempotent idempotent calls where fast-fail isn't needed.

**Usage:**

```python
from lexigram.resilience import CircuitBreaker

breaker = CircuitBreaker(CircuitBreakerConfig(failure_threshold=3))
async with breaker.protect():
    result = await risky_call()
```

## Retry

**What it is:** Re-executes a failed operation with exponential backoff and jitter.

**Config (`RetryConfig`):**

```python
from lexigram.contracts.infra.resilience.models import RetryConfig

RetryConfig(
    max_attempts=3,             # Total attempts including first
    base_delay=1.0,             # Initial delay in seconds
    max_delay=30.0,             # Max delay cap
    jitter=True,                # Add randomness to prevent thundering herd
    retry_on=(TimeoutError,),   # Exceptions that trigger retry
    abort_on=(ValueError,),     # Exceptions that skip retry
)
```

**When to use:** Transient failures — network timeouts, database deadlocks, rate limit 429s.

**When NOT to use:** Non-transient failures (validation errors, 4xx), idempotent-unsafe mutations.

**Usage:**

```python
from lexigram.resilience import retry

@retry(RetryConfig(max_attempts=3))
async def fetch_data(id: str) -> dict:
    ...
```

## Bulkhead

**What it is:** Isolates resources into fixed-size pools. If one pool is exhausted, other pools are unaffected.

**Config (`BulkheadConfig`):**

```python
from lexigram.resilience.config import BulkheadConfig

BulkheadConfig(
    max_concurrent=10,   # Max concurrent calls
    queue_size=100,      # Max queued waiters
    timeout=30.0,        # Queued wait timeout
)
```

**When to use:** Protecting thread pools or connection pools — ensuring one slow client can't exhaust shared resources.

**When NOT to use:** Single-tenant, low-concurrency applications.

## Rate limiter

**What it is:** Limits request rate using a token-bucket algorithm.

```python
from lexigram.resilience import RateLimiter

limiter = RateLimiter(rate=100)  # 100 requests per second
await limiter.acquire()
```

**When to use:** Protecting APIs from burst traffic, enforcing third-party API quotas.

**When NOT to use:** Low-traffic services, internal calls where the caller already limits.

## Timeout

**What it is:** Cancels operations that exceed a time budget. Throws `ResilienceTimeoutError`.

**Config (`TimeoutConfig`):**

```python
from lexigram.contracts.infra.resilience.models import TimeoutConfig

TimeoutConfig(
    timeout=30.0,        # Max execution time
)
```

**Usage:**

```python
from lexigram.resilience import with_timeout
from lexigram.resilience.exceptions import ResilienceTimeoutError

@with_timeout(5.0)
async def fast_call() -> dict:
    ...
```

**When to use:** Every external call. Always set a timeout.

**When NOT to use:** Never — every blocking operation should have a timeout.

## Throttle

**What it is:** Smooths request flow over a sliding window. Prevents burst traffic.

```python
from lexigram.resilience import Throttler, throttle

throttler = Throttler(max_rate=50, window_seconds=1)

@throttle(throttler)
async def throttled_call() -> None:
    ...
```

**When to use:** Rate-limited downstream APIs, protecting shared infrastructure.

**When NOT to use:** When rate limiting (token bucket) is a better semantic fit.

## Fallback

**What it is:** Returns a default value when the primary operation fails. Not a standalone pattern — combine with others via `ResiliencePipeline`.

## Pattern composition

Patterns compose via `ResiliencePipeline`:

```python
from lexigram.resilience.pipeline.executor import ResiliencePipeline
from lexigram.contracts.infra.resilience.models import RetryConfig, CircuitBreakerConfig, TimeoutConfig

pipeline = ResiliencePipeline(
    retry_config=RetryConfig(max_attempts=3),
    circuit_config=CircuitBreakerConfig(failure_threshold=3),
    timeout_config=TimeoutConfig(timeout=10.0),
)

result = await pipeline.execute(risky_call)
```

The `ResiliencePipelineFactoryProtocol` registers a factory in the DI container for consistent composition across services.

## Config examples

`application.yaml`:

```yaml
resilience:
  circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 30
  retry:
    max_attempts: 3
    base_delay: 1.0
    jitter: true
  bulkhead:
    max_concurrent: 10
    queue_size: 100
  timeout:
    timeout: 30.0
```

Env var override: `LEX_RESILIENCE__RETRY__MAX_ATTEMPTS=5`

## Testing resilience patterns

```python
from lexigram.resilience import CircuitBreaker
from lexigram.resilience.circuit import CircuitState

breaker = CircuitBreaker(CircuitBreakerConfig(failure_threshold=2))
assert breaker.state == CircuitState.CLOSED

with pytest.raises(ConnectionError):
    async with breaker.protect():
        raise ConnectionError

assert breaker.state == CircuitState.OPEN

import asyncio
breaker._half_open_after = 0.01
await asyncio.sleep(0.02)
assert breaker.state == CircuitState.HALF_OPEN
```

## See also

- `ResilienceProvider` — DI registration
- `ResilienceConfig` — top-level config model
- `CircuitBreakerRegistry` — named breaker management
- `CircuitOpenError`, `ResilienceTimeoutError`, `RetryExhaustedError` — leaf exceptions
