---
title: lexigram-cache Guide
description: Multi-backend caching for the Lexigram Framework — Redis, Memcached, in-memory, with stampede protection and tag-based invalidation
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `redis` | Recommended | Redis cache backend |
| `pymemcache` | Optional | Memcached cache backend |

## Overview

`lexigram-cache` provides a unified caching API across multiple backends. It handles the common caching patterns so you don't have to — stampede protection, TTL management, serialization, tag-based invalidation, and health checks.

### Mental Model

```
Application Code
     │
     ▼
  CacheService  ←  unified API (get/set/delete/delete_pattern)
     │
     ├── StampedeProtectedCache  ←  lock-based stampede prevention
     │
     ▼
  CacheBackendProtocol  ←  backend abstraction (Result-based)
     │
     ├── MemoryCacheBackend  (in-process, no deps)
     ├── RedisCacheBackend   (requires redis-py)
     └── MemcachedCacheBackend  (requires pymemcache)
```

## Core Concepts

### Backend Abstraction

All backends implement `CacheBackendProtocol` from `lexigram.contracts.infra.cache`. The protocol returns `Result[T, CacheError]` for every operation:

```python
from lexigram.contracts.infra.cache import CacheBackendProtocol
from lexigram.result import Ok, Err

# Backend returns Result — CacheService unwraps it internally
result = await backend.get("my-key")
if result.is_ok():
    value = result.unwrap()
```

| Backend | Extra | Storage |
|---------|-------|---------|
| `MemoryCacheBackend` | None | In-process dict |
| `RedisCacheBackend` | `lexigram-cache[redis]` | Redis server |
| `MemcachedCacheBackend` | `lexigram-cache[memcached]` | Memcached server |

### CacheService (High-Level API)

`CacheService` wraps the backend and provides ergonomic access:

```python
from lexigram.cache import CacheService

# Resolved from the container — inject via constructor
await cache.set("user:42", {"name": "Alice"}, ttl=300)
value = await cache.get("user:42")        # → {"name": "Alice"}
await cache.delete("user:42")             # → True
count = await cache.delete_pattern("user:*")  # → number of keys
```

`CacheService.get()` returns the raw value or `default` (not `Result`). Errors are logged and return the default — the service prefers graceful degradation over crashing.

### Named Backends

Configure multiple backends with different names in `CacheConfig.backends`. The first `default: true` backend is the default:

```yaml
cache:
  backends:
    - name: "hot"
      type: memory
      default: true
    - name: "persistent"
      type: redis
      host: localhost
      port: 6379
```

Resolve a specific backend:

```python
hot_cache = await container.resolve(CacheService, name="hot")
persistent_cache = await container.resolve(CacheService, name="persistent")
```

### Stampede Protection

When `service.enable_protection` is `True` (default), `CacheService` uses lock-based stampede protection. Only one process recomputes the value while others wait:

```python
cache.service:
  enable_protection: true
  protection_lock_ttl: 30
  protection_max_wait: 10.0
```

### Tag-Based Invalidation

Tag cache entries so you can invalidate groups of keys:

```python
from lexigram.cache import CacheService

await cache.set("article:1", data, tags=["articles", "breaking"])
await cache.set("article:2", data, tags=["articles"])

# Invalidate all articles
await cache.invalidate_tags(["articles"])

# The next get() for article:1 returns None
```

### Serialization

`CacheService` serializes values to JSON by default. JSON is the only built-in safe serializer — pickle is not available:

```python
cache.service:
  default_serializer: "json"    # default
```

Available serializers: `JSONSerializer` (default), `MsgPackSerializer` (optional, compact binary), `CompressingSerializer` (wraps another serializer with gzip/zlib). Objects reconstructed through `@cacheable` type tags are resolved only against the deny-by-default `lexigram.cache.serialization.DEFAULT_REGISTRY` (or the serializer's `allowed_classes` allowlist) — never through dynamic imports.

### Decorator Syntax

Decorate async functions with `@cache` or `@cacheable`:

```python
from lexigram.cache import cache, cacheable


@cache(ttl=300, tags=["user"])
async def get_user(user_id: str) -> dict:
    return await db.fetch_user(user_id)


@cacheable(ttl=60)
async def expensive_computation(input: str) -> str:
    # result is cached automatically
    return await compute(input)
```

## Typical Usage

### 1. Wire the cache

```python
from lexigram import Application
from lexigram.cache import CacheModule
from lexigram.cache.config import CacheConfig


def create_app() -> Application:
    app = Application(name="my-app")
    app.add_module(CacheModule.configure(CacheConfig(
        backends=[{
            "name": "default",
            "type": "memory",
            "default": True,
        }],
    )))
    return app
```

### 2. Use in a service

```python
from lexigram.di import inject
from lexigram.cache import CacheService


class UserService:
    @inject
    def __init__(self, cache: CacheService) -> None:
        self.cache = cache

    async def get_user(self, user_id: str) -> dict:
        cached = await self.cache.get(f"user:{user_id}")
        if cached is not None:
            return cached
        user = await self._load_from_db(user_id)
        await self.cache.set(f"user:{user_id}", user, ttl=300)
        return user
```

## Best Practices

- ✅ **Use `MemoryCacheBackend` for testing** — no external dependencies
- ✅ **Set `default_ttl`** on backends to prevent unbounded cache growth
- ✅ **Use tag-based invalidation** for group cache clearing
- ✅ **Enable stampede protection** for expensive-to-compute values
- ⚠️ **Cache only JSON-serializable values**; for non-serializable objects, register the value type in the deny-by-default type registry (`DEFAULT_REGISTRY`) or use a custom `AsyncStringSerializerProtocol`
- ❌ **Don't cache user secrets** (passwords, tokens) in plain text
- ❌ **Don't skip TTL** for volatile data — always set an expiration

## Next Steps

- [How-Tos](./HOWTOS.md) — Redis setup, stampede protection, multi-backend
- [Configuration](./CONFIGURATION.md) — all configuration keys
- [Troubleshooting](./TROUBLESHOOTING.md) — common errors and fixes
