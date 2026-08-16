# lexigram-testing

Centralized testing infrastructure for Lexigram Framework — Fixtures, factories, and utilities.

---

## Overview

`lexigram-testing` provides in-process fakes for common framework protocols (`FakeCache`, `FakeEventBus`, `FakeCommandBus`, `FakeClock`, …), a pytest plugin with auto-registered fixtures, deterministic data-factory helpers, and a `ContainerTestFixture` for DI integration tests.

---

> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add --dev lexigram-testing

# With extras for specific backends
uv add --dev "lexigram-testing[db]"      # aiosqlite, asyncpg
uv add --dev "lexigram-testing[web]"     # httpx, starlette
uv add --dev "lexigram-testing[ai]"      # lexigram-ai
uv add --dev "lexigram-testing[auth]"    # lexigram-auth
```

## Quick Start

```python
import pytest
from lexigram.testing.fixtures import fake_cache
from lexigram.testing.fakes import FakeCache


class TestUserService:
    @pytest.fixture
    def cache(self) -> FakeCache:
        return FakeCache()

    @pytest.fixture
    def service(self, cache: FakeCache) -> UserService:
        return UserService(cache=cache)

    @pytest.mark.asyncio
    async def test_returns_cached_user(
        self, service: UserService, cache: FakeCache
    ) -> None:
        await cache.set("user:123", {"id": "123", "name": "Alice"})
        result = await service.find_cached("123")
        assert result.is_ok()
        assert result.unwrap().name == "Alice"
```

## Testing

```python
from lexigram.testing.fakes import FakeEventBus


@pytest.mark.asyncio
async def test_places_order_emits_event(self, fake_event_bus: FakeEventBus) -> None:
    service = OrderService(bus=fake_event_bus)
    await service.place(order)

    fake_event_bus.assert_published(OrderPlaced, order_id=order.id)
    assert len(fake_event_bus.published_of_type(OrderPlaced)) == 1
```

## Available Fakes

All fakes live in `lexigram.testing.fakes` and implement the async contracts of the real services.

| Class | Implements | Location |
|-------|-----------|----------|
| `FakeCache` | cache API (`async get/set/delete/clear`) | `lexigram.testing.fakes.cache` |
| `FakeEventBus` | in-process event bus; `published()`, `published_of_type()`, `assert_published()` | `lexigram.testing.fakes.events` |
| `FakeCommandBus` | command dispatch | `lexigram.testing.fakes.buses` |
| `FakeQueryBus` | query dispatch | `lexigram.testing.fakes.buses` |
| `FakeUnitOfWork` | unit-of-work context | `lexigram.testing.fakes.lifecycle` |
| `FakeClock` | deterministic clock | `lexigram.testing.fakes.clock` |
| `FakeConfig` | config overrides | `lexigram.testing.fakes.config` |
| `FakeLogger` | structlog-compatible logger | `lexigram.testing.fakes.logging` |
| `FakeMetricsCollector` | metrics recording | `lexigram.testing.fakes.monitoring` |
| `FakeStateStore` | state storage | `lexigram.testing.fakes.cache` |
| `FakeAuditLogger` | audit logging | `lexigram.testing.fakes.audit` |
| `FakeRotatableSecretStore` | secret storage with rotation | `lexigram.testing.fakes.secrets` |
| `FakeTracer` / `FakeSpan` | tracing | `lexigram.testing.fakes.tracing` |

## Key Features

- **Zero infrastructure** — all fakes run in-process; no Docker or external services needed
- **Assertion helpers** — `assert_published()`, `assert_not_published()`, `assert_published_once()`, `assert_events_in_order()`
- **Async-first** — all fakes implement the same `async` APIs as real backends
- **pytest plugin** — auto-registered fixtures and auto-skip for external-service markers (Redis, PostgreSQL, Elasticsearch, RabbitMQ, Meilisearch)
- **DB fixtures** — `database_provider`, `clean_database`, `db_transaction`, `mock_connection`, `sample_user_data` (with `[db]` extra)
- **Data factory** — `test_data.create_user()`, `create_task()`, `create_message()` via `lexigram.testing.lib`
- **Container fixture** — `ContainerTestFixture` with `mock()`/`get()` for DI integration tests
- **Reproducible** — deterministic IDs and timestamps for snapshot testing

## pytest Plugin

The plugin is loaded automatically via entry points — no manual wiring needed:

```bash
uv run pytest -m "not integration"   # unit tests only (fast)
uv run pytest -m integration         # integration tests
```

Tests marked with external-service markers (`redis`, `postgres`, `elasticsearch`, `rabbitmq`, `meilisearch`) are skipped automatically when the service is unreachable.

## Key Source Files

| File | What it contains |
|------|----------------|
| `src/lexigram/testing/plugins/pytest/` | pytest plugin entry point, markers, auto-skip hooks |
| `src/lexigram/testing/fixtures/core.py` | Auto-registered core fixtures (`fake_cache`, `fake_event_bus`, …) |
| `src/lexigram/testing/fixtures/container.py` | `ContainerTestFixture` |
| `src/lexigram/testing/fixtures/bed.py` | `TestEnvironment` builder (`use_provider`, `override`, `fake`) |
| `src/lexigram/testing/fixtures/db.py` | DB fixtures (`database_provider`, `clean_database`, …) |
| `src/lexigram/testing/fakes/events.py` | `FakeEventBus` |
| `src/lexigram/testing/fakes/buses.py` | `FakeCommandBus`, `FakeQueryBus` |
| `src/lexigram/testing/lib/factory.py` | `TestDataFactory` (`create_user`, `create_task`, …) |
