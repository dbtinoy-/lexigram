---
title: lexigram-testing How-Tos
description: Task-oriented recipes for testing with lexigram-testing
---

## Unit Test with FakeCache

```python
import pytest
from lexigram.testing import FakeCache


@pytest.mark.asyncio
async def test_cache_expiry() -> None:
    cache = FakeCache()

    await cache.set("key", "value", ttl=0.01)
    await asyncio.sleep(0.02)
    result = await cache.get("key")

    assert result is None
```

## Unit Test with FakeEventBus Assertions

```python
import pytest
from lexigram.testing import FakeEventBus


@pytest.mark.asyncio
async def test_event_publishing() -> None:
    bus = FakeEventBus()

    await bus.publish(UserCreatedEvent(user_id="abc"))

    bus.assert_published(UserCreatedEvent, count=1, user_id="abc")
    bus.assert_published_once(UserCreatedEvent, user_id="abc")
    bus.assert_not_published(EmailSent)
```

## Unit Test with TestEnvironment

```python
from lexigram.testing import TestEnvironment


async def test_service_with_events() -> None:
    env = await TestEnvironment().setup()

    service = MyService(event_bus=env.event_bus)
    result = await service.do_something()

    assert result.is_ok()
    env.event_bus.subscriber_count > 0
    env.teardown()
```

## Validate a Custom Cache Backend with Compliance Suite

```python
from lexigram.testing import CacheBackendCompliance


class TestMyRedisCache(CacheBackendCompliance):
    async def create_backend(self):
        return MyRedisCache("redis://localhost:6379/1")
```

## Test HTTP Endpoints with AppTestBed

```python
from lexigram.testing import AppTestBed


async def test_list_users() -> None:
    async with AppTestBed.from_factory(
        "my_app.app:create_app",
    ) as bed:
        resp = await bed.client.get("/api/v1/users")
        assert resp.status_code == 200
```

## Test with DI Overrides Using @override and @testbed

```python
from lexigram.testing import override, testbed


@testbed("my_app.app:create_app")
class TestPayments:

    @override(PaymentGateway, MockPaymentGateway(fail=True))
    async def test_payment_failure(self, bed):
        resp = await bed.client.post("/pay", json={"amount": 100})
        assert resp.status_code == 402
```

## Use FixedClock for Time-Sensitive Tests

```python
from datetime import UTC, datetime
from lexigram.testing import FixedClock


async def test_expiry_with_clock() -> None:
    clock = FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
    assert clock.now().year == 2026

    clock.advance(3600)  # advance by 1 hour
    assert clock.now().hour == 1

    clock.set(datetime(2027, 1, 1, tzinfo=UTC))
    assert clock.now().year == 2027
```

## Snapshot Test with SnapshotAsserter

```python
from lexigram.testing import SnapshotAsserter


async def test_api_response_snapshot() -> None:
    asserter = SnapshotAsserter()
    response = await fetch_data()
    asserter.assert_snapshot("list_users", response)
```

## Set up a test container with ContainerTestFixture

```python
from lexigram.testing import ContainerTestFixture

async def test_with_mocked_repository() -> None:
    async with ContainerTestFixture() as fixture:
        fixture.mock(UserRepository, FakeUserRepository())
        service = await fixture.get(UserService)

        result = await service.create(email="a@b.com")

        assert result.is_ok()
```

## Generate test data with TestDataFactory

```python
from lexigram.testing import TestDataFactory

def test_user_generation() -> None:
    user = TestDataFactory.create_user(
        username="alice",
        roles=["admin", "editor"],
    )
    assert user["username"] == "alice"
    assert "admin" in user["roles"]

def test_task_factory() -> None:
    task = TestDataFactory.create_task(priority="high")
    assert task["priority"] == "high"
    assert task["status"] == "pending"

def test_message_factory() -> None:
    msg = TestDataFactory.create_message(
        topic="order.created",
        payload={"order_id": "123"},
    )
    assert msg["topic"] == "order.created"
```

## Use AsyncTestHelper for polling and timeout checks

```python
from lexigram.testing import AsyncTestHelper

async def test_eventual_consistency() -> None:
    helper = AsyncTestHelper()

    # Poll until a condition is met (up to 5 seconds)
    condition_met = await helper.wait_for_condition(
        condition_func=lambda: len(queue) >= 3,
        timeout=5.0,
        interval=0.1,
    )
    assert condition_met, "Expected 3 items in queue"

    # Run multiple coroutines concurrently
    results = await helper.collect_async_results([
        fetch_data(1),
        fetch_data(2),
        fetch_data(3),
    ])

    # Enforce a timeout on a slow operation
    try:
        data = await helper.run_with_timeout(slow_operation(), timeout=2.0)
    except TimeoutError:
        print("Operation timed out")
```

## Use Integration Markers

```python
from lexigram.testing import requires_redis


@requires_redis
async def test_redis_backed_cache() -> None:
    cache = MyRedisCache()
    await cache.set("key", "value")
    assert await cache.get("key") == "value"
```

Available markers: `requires_redis`, `requires_postgres`, `requires_rabbitmq`, `requires_elasticsearch`, `requires_meilisearch`, `requires_smtp`, `requires_kafka`, `requires_minio`, `requires_mongodb`, `requires_qdrant`.

## Notes

- Fakes reset state between tests — create a new instance in each test
- `TestEnvironment.teardown()` clears registered handlers and log entries
- Compliance suites require the backend to be available at test time
- Use `AITestClient(max_tokens_per_run=...)` to prevent runaway LLM API costs in test suites
