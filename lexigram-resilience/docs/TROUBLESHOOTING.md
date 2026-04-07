---
title: lexigram-resilience Troubleshooting
description: Common errors, causes, and fixes for lexigram-resilience
sidebar:
  order: 6
---

## Circuit Breaker Open

```
CircuitOpenError: Circuit breaker is open
```

**Cause:** The circuit breaker reached its `failure_threshold` and entered open state. All calls are failing fast to protect the system.

**Fix:** Wait for `recovery_timeout` seconds for automatic half-open transition, or call `breaker.reset()`. Investigate the downstream service health.

**Exception:** `CircuitOpenError` (from `lexigram.resilience.exceptions`)

---

## Retries Exhausted

```
RetryExhaustedError: All retry attempts exhausted
```

**Cause:** The operation failed after `max_attempts` attempts. All retries were consumed.

**Fix:** Check the `last_error` attribute for the root cause. Increase `max_attempts`, adjust `abort_on`/`retry_on` configuration, or address the underlying service issue. Consider adding a circuit breaker upstream of the retry.

**Exception:** `RetryExhaustedError` (from `lexigram.resilience.exceptions`)

---

## Bulkhead Capacity Exceeded

```
BulkheadRejectedError: Bulkhead capacity exceeded
```

**Cause:** The bulkhead's `max_concurrent` limit and `queue_size` are both full. The call was rejected immediately.

**Fix:** Increase `max_concurrent` or `queue_size` in `BulkheadConfig`. If the system is genuinely overloaded, scale horizontally instead.

**Exception:** `BulkheadRejectedError` (from `lexigram.resilience.exceptions`)

---

## Operation Timed Out

```
ResilienceTimeoutError: Operation timed out after 30.0s
```

**Cause:** The operation exceeded the configured timeout budget.

**Fix:** Increase the `timeout` value in `TimeoutConfig`, or optimize the operation to return faster. Check whether a downstream dependency is slow.

**Exception:** `ResilienceTimeoutError` (from `lexigram.resilience.exceptions`)

---

## Rate Limiter Blocked

No exception — `acquire()` blocks the coroutine indefinitely until a token is available. Use `try_acquire()` with a fallback.

**Fix:** Increase the `RateLimiter` rate, or switch to `try_acquire()` with a timeout:

```python
if await limiter.try_acquire():
    ...
else:
    return {"error": "rate_limited"}, 429
```

---

## Idempotency Key Too Long

```
ValueError: Idempotency key exceeds maximum length of 256 characters
```

**Cause:** The generated idempotency key exceeds the 256-character limit.

**Fix:** Provide a shorter `key_func` to the `@idempotent` decorator, or increase `max_key_length` in `IdempotencyConfig`.

**Exception:** `ValueError`

---

## Duplicate Request Detected

Returns cached result without executing the function. This is by design.

**Exception:** `DuplicateRequestError` (from `lexigram.resilience.exceptions`)

---

## Common Configuration Mistakes

### Circuit breaker never opens

Check `expected_exception` — if the exceptions raised by your function are not in this tuple, they won't count as failures. Default is `(Exception,)`.

### Retry never fires

Check `abort_on` — if an exception matches `abort_on`, retry is skipped. Also verify `retry_on` includes the exception type being raised.

### Pipeline has no effect

Verify the `order` parameter includes the pattern you configured. A `timeout_config` with no "timeout" in the order list is silently ignored.
