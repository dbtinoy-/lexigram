---
title: lexigram-testing Guide
description: Fakes, compliance suites, test environments, and test clients for the Lexigram Framework
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `lexigram-sql` | Yes | SQL test utilities |

## The Problem `lexigram-testing` Solves

Testing a contract-based async framework means writing test doubles for every protocol — event buses, caches, databases, LLM clients, audit loggers, and more. `lexigram-testing` provides **ready-made fakes, in-memory implementations, compliance test suites, and pre-wired test environments** so you focus on testing your logic, not infrastructure.

**Mental model:** A testing toolkit that mirrors the framework's architecture. Every protocol has a fake; every fake can be used standalone or wired into the DI container; every real backend can be validated against a compliance suite.

---

## Core Concepts

### Fakes

Lightweight in-memory implementations of framework protocols. Usable standalone or wired into the container.

| Fake | What It Replaces | Key Features |
|------|-----------------|--------------|
| `FakeCache` | Redis, Memcached | TTL expiry, `assert_has_key()`, `assert_value()` |
| `FakeEventBus` | RabbitMQ, Kafka | Publish/subscribe, `assert_event_raised()` |
| `FakeCommandBus` | Command dispatch | Handler registration, async dispatch |
| `FakeQueryBus` | Query dispatch | Handler registration, async query |
| `FakeAuditLogger` | Audit store | In-memory log, `assert_contains()` |
| `FakeUnitOfWork` | Transaction manager | Commit/rollback tracking |
| `FakeConfig` | Configuration | Dict-backed settings |
| `FakeLogger` | structlog | `LogEntry` capture, assertion helpers |
| `FakeTracer` | OpenTelemetry | `FakeSpan` capture |
| `FakeMetricsCollector` | Prometheus | In-memory metrics |
| `FakeStateStore` | State store | Key-value with `assert_has_key()` |
| `Clock` / `FakeClock` / `SystemClock` | Time | Deterministic time control |

```python
from lexigram.testing import FakeCache, FakeEventBus

cache = FakeCache()
await cache.set("key", "value", ttl=60)
cache.assert_has_key("key")

bus = FakeEventBus()
await bus.publish(UserCreatedEvent(user_id="u1"))
bus.assert_published(UserCreatedEvent)
```

### In-Memory Implementations

Heavier counterparts to fakes — implement protocols more completely, suitable for compliance testing.

| Type | Implements |
|------|-----------|
| `InMemoryCacheBackend` | `CacheBackendProtocol` |
| `InMemoryEventBus` | `EventBusProtocol` with wildcard handlers |
| `InMemoryCommandBus` | `CommandBusProtocol` |
| `InMemoryQueryBus` | `QueryBusProtocol` |
| `InMemoryRepository` | `RepositoryProtocol` |
| `InMemoryUnitOfWork` | `UnitOfWorkProtocol` |
| `InMemoryAuditLogger` | `AuditLoggerProtocol` |
| `InMemoryDistributedLock` | `DistributedLockProtocol` |
| `InMemoryBlobStore` | `BlobStoreProtocol` |
| `InMemoryOutbox` | Outbox pattern |
| `MemoryProvider` | DI provider for memory backends |

### Compliance Suites

Parameterized pytest test classes that validate a backend correctly implements a protocol. Subclass and implement the factory method:

```python
from lexigram.testing import CacheBackendCompliance


class TestMyCache(CacheBackendCompliance):
    async def create_backend(self):
        return MyCustomCache()
```

Available suites: `CacheBackendCompliance`, `EventBusCompliance`, `DatabaseProviderCompliance`, `RepositoryCompliance`, `QueueBackendCompliance`, `TaskQueueCompliance`, `VectorStoreCompliance`, `SearchEngineCompliance`, `BlobStoreCompliance`, `DistributedLockCompliance`, `AuditLoggerCompliance`, `AuditStoreCompliance`, `FlagProviderCompliance`, `MiddlewareCompliance`, `NotificationChannelCompliance`, `WebhookDeliveryStoreCompliance`, `WebhookSubscriptionStoreCompliance`.

### Test Environments

| Environment | When to Use |
|-------------|-------------|
| `TestEnvironment` | Unit tests — pre-wired container with in-memory fakes |
| `IntegrationEnvironment` | Integration tests — real providers with optional fakes |
| `AppTestBed` | Full application tests — boots the real app with override support |

```python
from lexigram.testing import TestEnvironment


async def test_service():
    env = TestEnvironment()
    await env.setup()

    service = MyService(
        event_bus=env.event_bus,
        command_bus=env.command_bus,
    )
    result = await service.do_something()
    assert result.is_ok()

    # Inspect published events directly
    published = env.event_bus.subscribed_types
    assert UserCreatedEvent in published

    env.teardown()
```

### Test Clients

Pre-built test clients with test-specific features (budget controls, inspection):

| Client | Purpose |
|--------|---------|
| `WebTestBed` / `WebTestClient` | HTTP integration tests with the Lexigram web layer |
| `DatabaseTestBed` / `DatabaseTestClient` | Database integration tests |
| `AITestBed` / `AITestClient` | LLM integration tests with token budget enforcement |
| `TaskTestBed` / `TaskTestClient` | Background task integration tests |
| `AdminTestClient` | Admin API testing |

```python
from lexigram.testing import AITestClient

client = AITestClient(max_tokens_per_run=1000)
result = await client.complete("Summarize: ...")
```

### Assertion Helpers

```python
from lexigram.testing import (
    assert_ok,
    assert_err,
    assert_result_ok,
    assert_result_err,
    assert_result_ok_value,
    assert_result_err_type,
    assert_all_ok,
    assert_healthy,
)
```

These integrate with the `Result` pattern from `lexigram.result`:

```python
result = await my_service.find("user-123")
assert_result_ok(result)
user = result.unwrap()
assert user.name == "Alice"
```

### Pytest Plugin

`lexigram-testing` registers a pytest plugin (`lexigram.testing.plugins.pytest`) that provides:

- `@requires_redis`, `@requires_postgres`, `@requires_rabbitmq` — skip-if-unavailable marks
- `@override` + `@testbed` — class-decorator sugar for DI overrides

```python
from lexigram.testing import override, testbed


@testbed("my_app.app:create_app")
class TestAPI:

    @override(PaymentGateway, MockPaymentGateway())
    async def test_payment(self, bed):
        resp = await bed.client.post("/pay", json={"amount": 100})
        assert resp.status_code == 200
```

---

## Best Practices

- ✅ Use `FakeCache`, `FakeEventBus` etc. for unit tests — they are lightweight and assertion-rich
- ✅ Use `TestEnvironment` when you need a pre-wired container with multiple fakes
- ✅ Use compliance suites to validate custom backend implementations
- ✅ Use `assert_result_ok` / `assert_result_err` for Result-returning methods
- ✅ Use `FixedClock` to test time-sensitive logic deterministically
- ❌ Don't mock protocols — use fakes and memory implementations instead
- ❌ Don't test infrastructure behavior — compliance suites already cover that
