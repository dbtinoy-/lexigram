---
title: lexigram-cache How-Tos
description: Task-oriented recipes for multi-backend caching
---

## Set Up Redis Cache

```yaml
# application.yaml
cache:
  backends:
    - name: "redis-primary"
      type: redis
      default: true
      redis_host: "localhost"
      redis_port: 6379
      redis_password: "${REDIS_PASSWORD}"
      key_prefix: "myapp"
      default_ttl: 3600
```

```python
from lexigram.cache import CacheService

# Resolve from container
cache = await container.resolve(CacheService)
await cache.set("session:abc", user_session_data, ttl=1800)
session = await cache.get("session:abc")
```

## Use In-Memory Cache for Testing

```python
from lexigram import Application
from lexigram.cache import CacheModule

# No external dependencies — pure in-memory
test_module = CacheModule.stub()

async with Application.boot(
    name="test-app",
    modules=[test_module],
) as app:
    from lexigram.cache import CacheService

    cache = await app.container.resolve(CacheService)
    await cache.set("key", "value")
    assert await cache.get("key") == "value"
```

## Get/Set with TTL

```python
from lexigram.cache import CacheService


async def get_user(user_id: str, cache: CacheService) -> dict:
    key = f"user:{user_id}"
    cached = await cache.get(key)
    if cached is not None:
        return cached

    user = await load_user_from_db(user_id)
    await cache.set(key, user, ttl=300)  # 5 minute TTL
    return user
```

## Delete Keys by Pattern

```python
# Delete all user-related cache entries
deleted = await cache.delete_pattern("user:*")
print(f"Cleared {deleted} cached user entries")

# Delete all session entries
await cache.delete_pattern("session:*")
```

## Override Cache Backend

```python
from lexigram.cache.config import CacheConfig, CacheBackendConfig
from lexigram.cache.types import BackendType


def create_app() -> Application:
    config = CacheConfig(backends=[
        CacheBackendConfig(
            name="hot",
            type=BackendType.MEMORY,
            default=True,
            max_size=5000,
        ),
        CacheBackendConfig(
            name="cold",
            type=BackendType.REDIS,
            redis_host="redis.example.com",
            redis_port=6379,
        ),
    ])
    app = Application(name="my-app")
    app.add_module(CacheModule.configure(config))
    return app
```

Then use named resolution:

```python
hot_cache = await container.resolve(CacheService, name="hot")
cold_cache = await container.resolve(CacheService, name="cold")
```

## Use Decorator-Based Caching

```python
from lexigram.cache import cache, cacheable, invalidate_cache


@cache(ttl=300, tags=["articles"])
async def get_article(article_id: str) -> dict:
    return await fetch_from_db(article_id)


@cacheable(ttl=60)
async def expensive_query(query: str) -> list[dict]:
    return await run_expensive_search(query)


@invalidate_cache(tags=["articles"])
async def update_article(article_id: str, data: dict) -> None:
    await save_to_db(article_id, data)
    # All "articles" tagged cache entries are automatically invalidated
```

## Enable Stampede Protection

Stampede protection is enabled by default. Configure it for expensive-to-compute values:

```yaml
cache:
  service:
    enable_protection: true
    protection_lock_ttl: 60    # Longer TTL for expensive computations
    protection_max_wait: 30.0  # Wait up to 30 seconds
```

The protection ensures only one process recomputes the value when it expires. Other callers wait for the result.

## Use Request-Scoped Caching

```python
from lexigram.cache import cache_in_request, get_request_cache, clear_request_cache


async def handler(request):
    # Cache per-request to avoid repeated DB lookups
    cache_in_request("current_user", user_data)
    cached = get_request_cache("current_user")

    # Clear when done
    clear_request_cache()
```

## Configure Multi-Backend with Different Namespaces

```yaml
cache:
  backends:
    - name: "fast"
      type: memory
      default: true
      default_ttl: 60
    - name: "durable"
      type: redis
      key_prefix: "persistent"
      default_ttl: 86400  # 1 day
```

```python
fast_cache = await container.resolve(CacheService, name="fast")
durable_cache = await container.resolve(CacheService, name="durable")

await fast_cache.set("temp", data, ttl=60)        # auto-evicted quickly
await durable_cache.set("archive", data, ttl=86400)  # persists
```
