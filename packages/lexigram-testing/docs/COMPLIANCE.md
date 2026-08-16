---
title: lexigram-testing Compliance
description: Contract verification for protocol implementations — available suites, usage, and custom suites.
---

> **Alpha (0.1.x)** — MIT licensed. Public API may change before 1.0.

## What compliance test suites are

Compliance suites are **base test classes** that verify a protocol implementation against its contract. They ensure your custom backend (cache, event bus, database, etc.) behaves correctly across all edge cases — not just the happy path.

Each suite is a standard pytest class. Subclass it, implement the abstract factory method, and pytest discovers the tests automatically.

## Available suites

| Suite | Protocol verified | Factory method |
|-------|-------------------|----------------|
| `CacheBackendCompliance` | `CacheBackendProtocol` | `create_backend()` |
| `EventBusCompliance` | `EventBusProtocol` | `create_bus()` |
| `QueueBackendCompliance` | `QueueBackendProtocol` | `create_backend()` |
| `TaskQueueCompliance` | `TaskQueueProtocol` | `create_queue()` |
| `DatabaseProviderCompliance` | `DatabaseProviderProtocol` | `create_provider()` |
| `RepositoryCompliance` | `RepositoryProtocol` | `create_repository()` |
| `VectorStoreCompliance` | `VectorStoreProtocol` | `create_store()` |
| `SearchEngineCompliance` | `SearchEngineProtocol` | `create_engine()` |
| `BlobStoreCompliance` | `BlobStoreProtocol` | `create_store()` |
| `DistributedLockCompliance` | `DistributedLockProtocol` | `create_lock()` |
| `AuditLoggerCompliance` | `AuditLoggerProtocol` | `create_logger()` |
| `AuditStoreCompliance` | `AuditStoreProtocol` | `create_store()` |
| `WebhookDeliveryStoreCompliance` | `WebhookDeliveryStoreProtocol` | `create_store()` |
| `WebhookSubscriptionStoreCompliance` | `WebhookSubscriptionStoreProtocol` | `create_store()` |
| `MiddlewareCompliance` | `MiddlewareProtocol` | `create_middleware()` |
| `FlagProviderCompliance` | `FlagProviderProtocol` | `create_provider()` |
| `NotificationChannelCompliance` | `NotificationChannelProtocol` | `create_channel()` |

Import from `lexigram.testing.compliance`:

```python
from lexigram.testing import CacheBackendCompliance
from lexigram.testing import EventBusCompliance
```

## Using compliance suites with custom backends

Subclass the suite and implement the factory method. Pytest runs all inherited tests:

```python
from lexigram.testing import CacheBackendCompliance
from my_project import RedisCacheBackend

class TestRedisCacheCompliance(CacheBackendCompliance):
    async def create_backend(self):
        return RedisCacheBackend("redis://localhost:6379/15")
```

The suite verifies:

- `get`/`set` round-trip
- Missing key returns `None`
- TTL expiration
- `delete` removes keys
- `clear` empties the cache
- Concurrent access safety

## Writing a custom compliance suite

Create a base test class that exercises your protocol:

```python
import pytest
from lexigram.result import Ok
from lexigram.contracts.infra.cache import CacheBackendProtocol

class MyProtocolCompliance:
    @pytest.fixture
    async def backend(self) -> CacheBackendProtocol:
        return await self.create_backend()

    async def create_backend(self) -> CacheBackendProtocol:
        raise NotImplementedError  # Subclasses implement this

    @pytest.mark.asyncio
    async def test_set_and_get(self, backend: CacheBackendProtocol) -> None:
        result = await backend.set("key", b"value")
        assert result.is_ok()

        got = await backend.get("key")
        assert got.is_ok() and got.unwrap() == b"value"

    @pytest.mark.asyncio
    async def test_missing_key(self, backend: CacheBackendProtocol) -> None:
        result = await backend.get("nonexistent")
        assert result.is_ok() and result.unwrap() is None
```

Add it to your test suite's `__all__` and import it alongside the built-in suites.

## Example: verifying a custom cache backend

```python
from lexigram.testing import CacheBackendCompliance
from my_app.backends import MyCustomCache

class TestMyCacheCompliance(CacheBackendCompliance):
    async def create_backend(self):
        return MyCustomCache(max_size=1000)

# Run with: pytest tests/ --verbose
```

The compliance suite will run approximately 15-20 tests depending on the protocol. All tests use `Result`-based assertions:

```python
result = await backend.set("key", b"val")
assert result.is_ok()  # Never unwrap() without checking
```

## See also

- `lexigram.testing.compliance` — full module listing
- `lexigram.contracts.cache.CacheBackendProtocol` — protocol definition
- `FakeCache`, `InMemoryCacheBackend` — reference implementations for comparison
- `CacheBackendCompliance` — source to understand the test matrix
