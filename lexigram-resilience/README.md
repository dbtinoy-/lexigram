# lexigram-resilience

Resilience patterns for the Lexigram Framework (circuit breaker, retry, bulkhead, rate limiting, throttle, fallback)

---

## Overview

lexigram-resilience provides circuit breakers, retry policies, bulkhead isolation, timeouts, rate limiting, throttling, fallback patterns, resilience pipelines, and idempotency key management. All implementations are async-first and designed for high-concurrency workloads. Distributed backends are available for circuit breakers, rate limiters, and idempotency stores when shared state across instances is required.

---


> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add lexigram-resilience
# Optional extras
uv add "lexigram-resilience[idempotency-redis,idempotency-database]"
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module

# Import the module from the package
from lexigram.resilience import ResilienceModule

@module(imports=[ResilienceModule.configure()])
class AppModule(Module):
    pass

async with Application.boot(modules=[AppModule]) as app:
    # use app.container to resolve services
    ...
```

## Configuration

> **Zero-config usage:** Call `ResilienceModule.configure()` with no arguments to use defaults.

### Option 1 — YAML file

```yaml
# application.yaml
resilience:
  circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 60.0
  retry:
    max_attempts: 3
    base_delay: 1.0
  bulkhead:
    max_concurrent: 10
```

### Option 2 — Profiles + Environment Variables *(recommended)*

```bash
export LEX_RESILIENCE__ENABLED=true
# Environment variables for each field
```

### Option 3 — Python

```python
from lexigram.resilience.config import ResilienceConfig
from lexigram.resilience import ResilienceModule

config = ResilienceConfig(...)
ResilienceModule.configure(config)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `circuit_breaker.failure_threshold` | `5` | `LEX_RESILIENCE__CIRCUIT_BREAKER__FAILURE_THRESHOLD` | Failures required to open the circuit |
| `circuit_breaker.recovery_timeout` | `60.0` | `LEX_RESILIENCE__CIRCUIT_BREAKER__RECOVERY_TIMEOUT` | Seconds in open state before half-open probe |
| `circuit_breaker.success_threshold` | `3` | `LEX_RESILIENCE__CIRCUIT_BREAKER__SUCCESS_THRESHOLD` | Successes in half-open state to close the circuit |
| `retry.max_attempts` | `3` | `LEX_RESILIENCE__RETRY__MAX_ATTEMPTS` | Total attempts including initial call |
| `retry.base_delay` | `1.0` | `LEX_RESILIENCE__RETRY__BASE_DELAY` | Base delay between retries in seconds |
| `retry.max_delay` | `60.0` | `LEX_RESILIENCE__RETRY__MAX_DELAY` | Maximum retry delay cap in seconds |
| `retry.backoff_factor` | `2.0` | `LEX_RESILIENCE__RETRY__BACKOFF_FACTOR` | Exponential multiplier applied to base delay |
| `bulkhead.max_concurrent` | `10` | `LEX_RESILIENCE__BULKHEAD__MAX_CONCURRENT` | Maximum concurrent calls |
| `bulkhead.queue_size` | `100` | `LEX_RESILIENCE__BULKHEAD__QUEUE_SIZE` | Waiting queue depth before rejection |
| `timeout.timeout` | `30.0` | `LEX_RESILIENCE__TIMEOUT__TIMEOUT` | Default operation timeout in seconds |
| `idempotency.ttl` | `3600` | `LEX_RESILIENCE__IDEMPOTENCY__TTL` | Cached result TTL in seconds |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `ResilienceModule.configure(config)` | Configure with explicit ResilienceConfig |
| `ResilienceModule.stub()` | Minimal config for testing |

## Key Features

- **CircuitBreaker** — Opens circuit after repeated failures, prevents cascading failures
- **CircuitBreakerRegistry** — Named circuit breaker lookup and management
- **RetryPolicy** — Exponential backoff, jitter, retry on specific exceptions
- **Bulkhead** — Semaphore-based concurrency limiting with queue support
- **TimeoutManager** — Async context manager for operation timeouts
- **RateLimiter** — Token bucket, sliding window, and distributed rate limiting
- **Throttler** — Request throttling with configurable limits and windows
- **ResiliencePipeline** — Composable pipeline chaining multiple resilience patterns
- **Idempotency subsystem** — Idempotency key management with in-memory, database, and Redis backends

## Testing

```python
async with Application.boot(modules=[ResilienceModule.stub()]) as app:
    # your test code
    ...
```

In-memory backends are safe for testing with no external dependencies:

```python
from lexigram.resilience import (
    InMemoryCircuitBreakerBackend,
    InMemoryIdempotencyStore,
)

cb = CircuitBreaker(name="test_cb")  # Uses InMemoryCircuitBreakerBackend
store = InMemoryIdempotencyStore()   # Local-only
```

## Key Source Files

| File | What it contains |
|------|----------------|
| `src/lexigram/resilience/module.py` | `ResilienceModule` class with factory methods |
| `src/lexigram/resilience/di/provider.py` | `ResilienceProvider` — wires resilience protocols into DI container |
| `src/lexigram/resilience/config.py` | `ResilienceConfig` and `BulkheadConfig` |
| `src/lexigram/resilience/circuit/` | Circuit breaker implementations (in-memory + distributed backends) |
| `src/lexigram/resilience/retry/` | Retry policy implementations with backoff strategies |
| `src/lexigram/resilience/bulkhead/` | Bulkhead semaphore-based concurrency control |
| `src/lexigram/resilience/rate_limiter/` | Token bucket, sliding window, distributed rate limiters |
| `src/lexigram/resilience/idempotency/` | Idempotency decorator, stores, middleware, config |