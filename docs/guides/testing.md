---
title: "Testing Strategies"
description: "Fast, decoupled tests with fakes, test clients, and protocol compliance suites."
---

Lexigram is built for testability. Because services depend on **protocols** and are wired by the container, you can replace any infrastructure dependency with an in-memory implementation and run your tests entirely in-process. The `lexigram-testing` package provides the building blocks.

---

## 1. Fakes Over Mocks

Lexigram favours **fakes** — real, in-memory implementations of a protocol — over mocks that merely record calls. Fakes behave like the real thing (you can read back what you wrote), so your tests exercise genuine logic at unit-test speed.

| Test type | Dependencies | Speed |
|-----------|--------------|-------|
| **Unit** | Fakes for everything | Fastest |
| **Integration** | Real backends (Postgres, Redis) | Slower |
| **End-to-end** | A booted app via a test client | Slowest |

---

## 2. Built-in Fakes

`lexigram-testing` ships fakes for the common contracts:

```python
from lexigram.testing import (
    FakeCache,          # CacheBackendProtocol
    FakeEventBus,       # EventBusProtocol
    FakeClock,          # ClockProtocol (manually advanced)
    FixedClock,         # ClockProtocol (frozen at a fixed time)
    FakeLogger,
    FakeCommandBus,
    FakeQueryBus,
    FakeUnitOfWork,
    FakeMetricsCollector,
)
```

Use a fake exactly where the real implementation would go — inject it as the protocol:

```python
import pytest
from lexigram.testing import FakeCache
from my_app.services import OrderService


@pytest.mark.asyncio
async def test_order_is_cached():
    cache = FakeCache()
    service = OrderService(cache=cache)

    await service.place_order(order_id="123")

    # FakeCache implements CacheBackendProtocol — read the value straight back
    cached = await cache.get("order:123")
    assert cached.unwrap() is not None
```

`FakeEventBus` records the events your code publishes; consult the [`lexigram-testing` package docs](/packages/lexigram-testing/) for its inspection helpers.

---

## 3. Controlling Time

For expiry, scheduling, or timestamp logic, inject a deterministic clock instead of the system clock:

```python
from datetime import datetime, UTC
from lexigram.testing import FixedClock

clock = FixedClock(datetime(2026, 1, 1, 12, 0, tzinfo=UTC))
service = TokenService(clock=clock)

token = await service.create_token(ttl_seconds=3600)
assert token.expires_at == datetime(2026, 1, 1, 13, 0, tzinfo=UTC)
```

`FakeClock` is the manually-advanceable variant when you need to simulate the passage of time within a test.

---

## 4. Overriding Services in the Container

When you boot the real application but want to replace one dependency, use a `testing_mode` container and `override()`:

```python
from lexigram import Container

container = Container(testing_mode=True)
container.override(UserRepository, FakeUserRepository())
```

`override()` is only available when `testing_mode=True`, so it can never be used by accident in production.

Modules expose `stub()` for the same purpose at the module level — it returns a test-mode variant backed by in-memory/no-op providers:

```python
from lexigram import Application
from lexigram.tenancy import TenancyModule

async with Application.boot(modules=[TenancyModule.stub()]) as app:
    ...
```

---

## 5. Test Clients

`lexigram-testing` provides per-subsystem **test beds** and **clients** that boot the relevant providers in-process:

| Client | Bed | For |
|--------|-----|-----|
| `WebTestClient` | `WebTestBed` | Sending requests to your controllers without a real server |
| `DatabaseTestClient` | `DatabaseTestBed` | Repository tests against a throwaway database |
| `TaskTestClient` | `TaskTestBed` | Enqueue/execute background tasks |
| `AITestClient` | `AITestBed` | Drive AI services with a stubbed LLM |

```python
from lexigram.testing import WebTestBed


async def test_get_profile():
    async with WebTestBed(create_app) as bed:
        client = bed.client
        response = await client.get("/api/profile")
        assert response.status_code == 200
```

See the package docs for each bed's exact setup options.

---

## 6. Protocol Compliance Suites

A standout feature of `lexigram-testing`: reusable **compliance suites** that verify *your* implementation of a protocol behaves correctly. Run the suite against your backend to guarantee it honours the contract:

```python
from lexigram.testing import CacheBackendCompliance
from my_app.infrastructure.cache import MyCustomCache


class TestMyCacheCompliance(CacheBackendCompliance):
    def make_backend(self):
        return MyCustomCache()
```

Compliance suites ship for caches, repositories, event buses, queues, vector stores, search engines, audit stores, and more — so custom implementations stay drop-in compatible.

---

## 7. Separating Test Tiers

Mark slower, infrastructure-dependent tests so you can run the fast suite during development:

```bash
# Default — runs unit tests only (integration-marked tests deselected)
uv run pytest

# Explicit form (equivalent)
uv run pytest -m "not integration"

# Only integration tests (requires docker compose up -d)
uv run pytest -m integration
```

### Scenario Suite

The `tests/integration/scenarios/` directory contains **cross-package integration tests** that run entirely in-memory — no live Postgres, Redis, or Docker required. Each scenario boots a minimal Lexigram application configured for a specific package composition (CRUD, events, web auth, audit, cache, tasks, tenancy).

```bash
# Run scenario tests
uv run pytest tests/integration/scenarios/ -v

# Or include them via the integration marker
uv run pytest -m integration -k "scenario"
```

### Running Specific Packages

```bash
# One package's unit tests
uv run pytest packages/lexigram-web/tests/

# One file
uv run pytest tests/dev/test_registry.py -v

# One test
uv run pytest tests/dev/test_registry.py::test_audit_registry_contains_expected_generators -v
```

---

## Next Steps

- [`lexigram-testing` package](/packages/lexigram-testing/) — full fixture and helper reference
- [Dependency Injection](/fundamentals/dependency-injection/) — `testing_mode` and `override()`
- [Result Pattern](/fundamentals/result-pattern/) — asserting on `Ok` / `Err`
