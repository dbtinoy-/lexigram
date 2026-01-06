---
title: lexigram-testing Troubleshooting
description: Common testing errors, their causes, and how to fix them
---

## Test Suite Not Discovering Compliance Tests

**Cause:** You subclassed a compliance suite but didn't name the class with a `Test` prefix, or the factory method is not implemented.

**Solution:**
```python
from lexigram.testing import CacheBackendCompliance


# ✅ Correct — class must start with "Test"
class TestMyRedisCache(CacheBackendCompliance):
    async def create_backend(self):
        return RedisCacheBackend("redis://localhost:6379/15")
```

## `TokenBudgetExceededError` in AI Tests

**Exception:** `lexigram.testing.TokenBudgetExceededError`

**Cause:** `AITestClient` hit its token budget cap, preventing runaway API costs.

**Solution:**
```python
# Increase or disable the budget
client = AITestClient(max_tokens_per_run=0)  # 0 = no limit
```

## `FakeEventBus.assert_event_raised()` Fails

**Cause:** The event was never published, or the event type doesn't match.

**Solution:**
```python
bus = FakeEventBus()
await bus.publish(UserCreatedEvent(user_id="u1"))

# Check the exact event type
bus.assert_event_raised(UserCreatedEvent)

# Inspect published events
assert len(bus.events) == 1
```

## `TestEnvironment` Throws on `resolve()`

**Cause:** The requested type was not registered in the container.

**Solution:**
```python
env = await TestEnvironment().setup()

# Resolve by concrete type (registered as singleton)
bus = await env.container.resolve(InMemoryEventBus)

# Or resolve by protocol
from lexigram.contracts.events import EventBusProtocol
bus = await env.container.resolve(EventBusProtocol)
```

## Integration Test Fails with Service Unavailable

**Cause:** A required external service (Redis, PostgreSQL, RabbitMQ) is not running.

**Solution:**
```python
from lexigram.testing import requires_redis


# Skip if Redis is unavailable
@requires_redis
async def test_with_redis() -> None:
    ...
```

## Snapshot Assertions Fail Unexpectedly

**Exception:** `lexigram.testing.SnapshotMismatchError`

**Cause:** The actual output differs from the stored snapshot.

**Solution:** Review the diff in the error message. If the change is expected, update snapshots by deleting the snapshot file and re-running.

## Pytest marker not skipping when service unavailable

**Symptom:** Tests decorated with `@requires_redis` or `@requires_postgres` run (and fail) instead of being skipped when the external service is not available.

**Cause:** The marker is registered by `lexigram-testing`'s pytest plugin, but the plugin is not loaded. This happens when `lexigram-testing` is not installed in the test environment's Python path, or when pytest is run without `-p lexigram.testing.plugin`.

**Fix:** Ensure the plugin is loaded:

```bash
# Auto-discovered when lexigram-testing is installed
uv run pytest ...

# Or load explicitly
uv run pytest -p lexigram.testing.plugin ...
```

Verify the markers are registered:

```bash
uv run pytest --markers | grep requires_
```

## Snapshot mismatch in CI vs local

**Symptom:** Snapshot tests pass locally but fail in CI with a diff that shows only whitespace or formatting differences.

**Cause:** The snapshot contains platform-dependent output — different line endings (CRLF vs LF), Python version differences, or locale-specific formatting.

**Fix:** Normalize output before snapshotting:

```python
from lexigram.testing import SnapshotAsserter

asserter = SnapshotAsserter()
# Normalizes line endings and platform-dependent output
normalized = asserter.normalize(await service.process(data))
asserter.assert_match(normalized, snapshot)
```

Or update the snapshot in CI by deleting the old `.snap` file and re-running.

## Async fixtures sharing state between tests

**Symptom:** Tests pass individually but fail when run together — state from one test leaks into another.

**Cause:** An async fixture created a mutable object at module scope instead of recreating it per test. `TestEnvironment` is shared across tests in the same module unless fixture scope is explicitly set.

**Fix:** Use `scope="function"` (default) on fixtures that create mutable state:

```python
import pytest


@pytest.fixture
async def env():
    return await TestEnvironment().setup()  # fresh per test
```

Avoid module-level state:

```python
# ❌ Wrong — shared across tests
_env = TestEnvironment()

# ✅ Correct — created per test
@pytest.fixture
async def env():
    return await TestEnvironment().setup()
```

## Compliance test fails on empty collection

**Symptom:** A `CacheBackendCompliance` or `DatabaseBackendCompliance` test fails with an assertion error on the first test method.

**Cause:** The `create_backend()` factory returns a backend connected to a database or cache that already contains data from previous tests. Compliance suites assume a clean state.

**Fix:** Ensure the factory creates an isolated backend with no pre-existing data:

```python
class TestMyRedisCache(CacheBackendCompliance):
    async def create_backend(self):
        backend = RedisCacheBackend("redis://localhost:6379/15")
        await backend.clear()  # start clean
        return backend
```

Or use a separate database index/database per test class.
