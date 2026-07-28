# lexigram-testing

Centralized testing infrastructure for Lexigram Framework — Fixtures, factories, and utilities.

---

## Overview

`lexigram-testing` provides ready-made fake implementations for every core protocol so unit tests stay fast, isolated, and free of real infrastructure. It ships with a pytest plugin for auto-discovered fixtures, factory helpers for domain objects, and a `TestContainer` builder for integration-test DI.

---


> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add --dev lexigram-testing

# With extras for specific backends
uv add --dev "lexigram-testing[db]"    # aiosqlite, asyncpg
uv add --dev "lexigram-testing[web]"   # httpx, starlette
uv add --dev "lexigram-testing[ai]"     # lexigram-ai
```

## Quick Start

```python
import pytest
from lexigram.testing.fixtures import (
    fake_cache,
    fake_db,
    fake_event_bus,
    fake_task_queue,
)


class TestUserService:
    @pytest.fixture
    def cache(self) -> FakeCacheBackend:
        return FakeCacheBackend()

    @pytest.fixture
    def service(self, cache: FakeCacheBackend) -> UserService:
        return UserService(cache=cache)

    @pytest.mark.asyncio
    async def test_returns_cached_user(self, service: UserService, cache: FakeCacheBackend) -> None:
        await cache.set("user:123", {"id": "123", "name": "Alice"})
        result = await service.find_cached("123")
        assert result.is_ok()
        assert result.unwrap().name == "Alice"
```

## Testing

```python
from lexigram import Application
from lexigram.testing.clients.cache import FakeCacheBackend
from lexigram.testing.clients.events import FakeEventBus
from lexigram.testing.clients.tasks import FakeTaskQueue


@pytest.mark.asyncio
async def test_places_order_emits_event(self, fake_event_bus: FakeEventBus) -> None:
    service = OrderService(bus=fake_event_bus)
    await service.place(order)

    assert fake_event_bus.published_count("OrderPlaced") == 1
    event = fake_event_bus.last_published("OrderPlaced")
    assert event.order_id == order.id


@pytest.mark.asyncio
async def test_enqueues_welcome_email(self, fake_queue: FakeTaskQueue) -> None:
    service = UserService(queue=fake_queue)
    await service.register(new_user)

    assert fake_queue.enqueued_count("send_welcome_email") == 1
    job = fake_queue.last_enqueued("send_welcome_email")
    assert job.kwargs["email"] == new_user.email
```

## Available Fakes

| Class | Implements | Location |
|-------|-----------|----------|
| `FakeCacheBackend` | `CacheBackend` | `lexigram.testing.clients.cache` |
| `FakeDatabase` | `DatabaseProviderProtocol` | `lexigram.testing.clients.db` |
| `FakeEventBus` | `EventBusProtocol` | `lexigram.testing.clients.events` |
| `FakeCommandBus` | `CommandBusProtocol` | `lexigram.testing.clients.events` |
| `FakeQueryBus` | `QueryBusProtocol` | `lexigram.testing.clients.events` |
| `FakeTaskQueue` | `TaskQueueProtocol` | `lexigram.testing.clients.tasks` |
| `FakeTokenManager` | `TokenManager` | `lexigram.testing.clients.auth` |
| `FakeSearchEngine` | `SearchEngineProtocol` | `lexigram.testing.clients.search` |
| `FakeAIClient` | `LLMClientProtocol` | `lexigram.testing.clients.ai` |
| `FakeSecretStore` | `SecretStoreProtocol` | `lexigram.testing.clients.auth` |

## Key Features

- **Zero infrastructure** — all fakes run in-process; no Docker or external services needed
- **Assertion helpers** — `published_count()`, `last_published()`, `enqueued_count()`, etc.
- **Async-first** — all fakes implement the same `async` protocols as real backends
- **pytest plugin** — auto-registered fixtures and `@pytest.mark.integration` marker
- **Factory helpers** — `UserFactory`, `OrderFactory`, etc. via `lexigram.testing.data`
- **Container builder** — `TestContainer.from_providers([...])` for integration-test DI
- **Reproducible** — deterministic IDs and timestamps for snapshot testing

## pytest Plugin

```ini
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = [
    "integration: marks tests as integration tests (deselect by default)",
]
```

```bash
uv run pytest -m "not integration"   # unit tests only (fast)
uv run pytest -m integration         # integration tests
```

## Key Source Files

| File | What it contains |
|------|----------------|
| `src/lexigram/testing/plugins/pytest.py` | pytest plugin entry point |
| `src/lexigram/testing/fixtures.py` | Auto-discovered pytest fixtures |
| `src/lexigram/testing/clients/cache.py` | `FakeCacheBackend` |
| `src/lexigram/testing/clients/db.py` | `FakeDatabase` |
| `src/lexigram/testing/clients/events.py` | `FakeEventBus`, `FakeCommandBus`, `FakeQueryBus` |
| `src/lexigram/testing/clients/tasks.py` | `FakeTaskQueue` |
| `src/lexigram/testing/clients/ai.py` | `FakeAIClient` |
| `src/lexigram/testing/data/__init__.py` | Factory helpers |