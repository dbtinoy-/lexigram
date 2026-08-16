---
title: lexigram-testing Quickstart
description: Install lexigram-testing and write your first test with fakes and test environments
---

:::tip[Alpha]
Lexigram is **alpha (0.1.x)**. Pin versions in production and expect public APIs to evolve before 1.0.
:::

## Install

```bash
uv add --dev lexigram-testing
```

For optional extras (web, database, auth, cache, storage, AI):

```bash
uv add --dev "lexigram-testing[web,db]"
```

## Hello World — FakeCache

```python
import pytest
from lexigram.testing import FakeCache


@pytest.mark.asyncio
async def test_cache_roundtrip() -> None:
    cache = FakeCache()

    await cache.set("greeting", "hello", ttl=60)
    value = await cache.get("greeting")

    assert value == "hello"
    cache.assert_has_key("greeting")
```

## Primary Import + TestEnvironment

```python
from lexigram.testing import TestEnvironment


async def test_with_env() -> None:
    env = TestEnvironment()
    await env.setup()

    # Fakes are pre-wired into the container
    service = MyService(event_bus=env.event_bus)
    await service.do_something()

    env.teardown()
```

## What Just Happened

- `FakeCache` provided an in-memory cache implementation for fast, deterministic tests
- `TestEnvironment` created a pre-wired DI container with in-memory fakes for event bus, command bus, query bus, audit logger, and distributed lock
- No infrastructure setup required — no Redis, no database, no external services

## Next Steps

- [Guide](./GUIDE.md) — fakes, compliance suites, test clients, and test environments
- [How-Tos](./HOWTOS.md) — task-oriented recipes
