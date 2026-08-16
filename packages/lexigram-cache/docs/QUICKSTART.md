---
title: lexigram-cache Quickstart
description: Install and configure multi-backend caching for your Lexigram application
---

:::note[What you'll learn]
- Install `lexigram-cache` with `uv`
- Wire the cache with `CacheModule` or `CacheProvider`
- Get, set, and delete cache entries with TTL
:::

## Install

```bash
uv add lexigram-cache
```

:::tip
For Redis backend support, add the optional dependency:

```bash
uv add lexigram-cache[redis]
```

For Memcached: `uv add lexigram-cache[memcached]`. For semantic caching with FAISS: `uv add lexigram-cache[semantic]`.
:::

## Minimal Setup — CacheModule

```python
import asyncio
from lexigram import Application
from lexigram.cache import CacheModule

async def main():
    async with Application.boot(
        name="my-app",
        modules=[CacheModule.configure()],
    ) as app:
        from lexigram.cache import CacheService

        cache = await app.container.resolve(CacheService)
        await cache.set("greeting", "Hello, Lexigram!")
        value = await cache.get("greeting")
        print(value)  # "Hello, Lexigram!"

asyncio.run(main())
```

## Using CacheProvider Directly

```python
from lexigram import Application
from lexigram.cache import CacheProvider


def create_app() -> Application:
    app = Application(name="my-app")
    app.add_provider(CacheProvider())
    return app
```

## Testing with CacheModule.stub()

```python
from lexigram.cache import CacheModule

# In-memory backend with no external connections
test_module = CacheModule.stub()
```

## Next Steps

- [Guide](./GUIDE.md) — caching concepts and workflows
- [How-Tos](./HOWTOS.md) — Redis, Memcached, stampede protection recipes
- [Configuration](./CONFIGURATION.md) — all configuration keys
