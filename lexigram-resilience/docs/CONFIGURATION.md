---
title: lexigram-resilience Configuration
description: All config fields for lexigram-resilience
sidebar:
  order: 4
---

The config section is `"resilience"`. Environment variable prefix is `LEX_RESILIENCE__`.

## ResilienceConfig

Top-level config. Root section in `application.yaml`:

```yaml
resilience:
  circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 60.0
  retry:
    max_attempts: 3
    base_delay: 1.0
  bulkhead:
    max_concurrent: 10
  timeout:
    timeout: 30.0
```

### circuit_breaker

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `failure_threshold` | `int` | `5` | `LEX_RESILIENCE__CIRCUIT_BREAKER__FAILURE_THRESHOLD` | Failures before the circuit opens |
| `recovery_timeout` | `float` | `60.0` | `LEX_RESILIENCE__CIRCUIT_BREAKER__RECOVERY_TIMEOUT` | Seconds in OPEN state before HALF-OPEN |
| `expected_exception` | `tuple[type[Exception], ...]` | `(Exception,)` | — | Exception types counted as failures |
| `success_threshold` | `int` | `3` | `LEX_RESILIENCE__CIRCUIT_BREAKER__SUCCESS_THRESHOLD` | Consecutive successes to close from half-open |
| `timeout` | `float` | `30.0` | `LEX_RESILIENCE__CIRCUIT_BREAKER__TIMEOUT` | Per-call timeout in seconds |
| `name` | `str` | `""` | — | Human-readable identifier |
| `sliding_window_seconds` | `float` | `60.0` | `LEX_RESILIENCE__CIRCUIT_BREAKER__SLIDING_WINDOW_SECONDS` | Window for computing failure rate |
| `failure_rate_threshold` | `float` | `0.5` | `LEX_RESILIENCE__CIRCUIT_BREAKER__FAILURE_RATE_THRESHOLD` | Fraction of calls that must fail to trip |
| `backend` | `Literal["memory", "redis", "consul"]` | `"memory"` | — | Distributed coordination backend |

### retry

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `max_attempts` | `int` | `3` | `LEX_RESILIENCE__RETRY__MAX_ATTEMPTS` | Total attempts including initial try |
| `base_delay` | `float` | `1.0` | `LEX_RESILIENCE__RETRY__BASE_DELAY` | Initial delay in seconds |
| `max_delay` | `float` | `60.0` | `LEX_RESILIENCE__RETRY__MAX_DELAY` | Maximum delay cap |
| `backoff_factor` | `float` | `2.0` | `LEX_RESILIENCE__RETRY__BACKOFF_FACTOR` | Exponential backoff multiplier |
| `jitter` | `bool | float` | `True` | `LEX_RESILIENCE__RETRY__JITTER` | Jitter as fraction of delay (`True` = 25%) |
| `retry_on` | `tuple[type[Exception]]` | `(Exception,)` | — | Exception types that trigger retry |
| `abort_on` | `tuple[type[Exception]]` | `()` | — | Exception types that abort retry |
| `retry_on_result` | `Callable | None` | `None` | — | Predicate: retry if result matches |
| `abort_if` | `Callable | None` | `None` | — | Predicate: abort if result matches |

### bulkhead

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `max_concurrent` | `int` | `10` | `LEX_RESILIENCE__BULKHEAD__MAX_CONCURRENT` | Maximum concurrent requests |
| `queue_size` | `int` | `100` | `LEX_RESILIENCE__BULKHEAD__QUEUE_SIZE` | Maximum queue size |
| `timeout` | `float` | `30.0` | `LEX_RESILIENCE__BULKHEAD__TIMEOUT` | Execution timeout |
| `name` | `str` | `""` | — | Bulkhead name |

### timeout

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `timeout` | `float` | `30.0` | `LEX_RESILIENCE__TIMEOUT__TIMEOUT` | Operation timeout in seconds |
| `timeout_message` | `str` | `"Operation timed out"` | — | Timeout error message |

## IdempotencyConfig

Configured separately through `IdempotencyConfig` or via `IdempotencyProvider`. Env prefix `LEX_RESILIENCE__IDEMPOTENCY__`.

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `ttl` | `int` | `3600` | `LEX_RESILIENCE__IDEMPOTENCY__TTL` | TTL for cached results (seconds) |
| `max_entries` | `int` | `10000` | `LEX_RESILIENCE__IDEMPOTENCY__MAX_ENTRIES` | Max in-memory entries before FIFO eviction |
| `cleanup_interval` | `float` | `300.0` | `LEX_RESILIENCE__IDEMPOTENCY__CLEANUP_INTERVAL` | Background cleanup sweep interval |
| `auto_cleanup` | `bool` | `True` | `LEX_RESILIENCE__IDEMPOTENCY__AUTO_CLEANUP` | Start background cleanup on init |
| `key_prefix` | `str` | `"idempotency:"` | `LEX_RESILIENCE__IDEMPOTENCY__KEY_PREFIX` | Prefix for backing-store keys |
| `max_key_length` | `int` | `512` | `LEX_RESILIENCE__IDEMPOTENCY__MAX_KEY_LENGTH` | Maximum idempotency key length |

## Example: application.yaml

```yaml
resilience:
  circuit_breaker:
    failure_threshold: 10
    recovery_timeout: 30.0
    backend: "memory"
  retry:
    max_attempts: 5
    base_delay: 0.5
    backoff_factor: 1.5
  bulkhead:
    max_concurrent: 20
    queue_size: 200
  timeout:
    timeout: 15.0
```

Env var override form:

```bash
export LEX_RESILIENCE__RETRY__MAX_ATTEMPTS=5
export LEX_RESILIENCE__CIRCUIT_BREAKER__RECOVERY_TIMEOUT=30.0
```
