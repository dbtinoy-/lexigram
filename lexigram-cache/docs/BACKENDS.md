---
title: lexigram-cache Backends
description: Compare Redis, Memcached, and in-memory backends for lexigram-cache
sidebar:
  order: 3
---

`lexigram-cache` provides three cache backends behind the `CacheBackendProtocol` contract. All expose the same `Result`-based API, support TTLs, key prefixes, and pluggable serialization.

## Supported Backends

| Backend | Extra | Driver | Production-ready | Best for |
|---------|-------|--------|-----------------|----------|
| Redis | `lexigram-cache[redis]` | `redis>=5.0.0` | Yes | Distributed caching, multi-service deployments |
| Memcached | `lexigram-cache[memcached]` | `pymemcache>=4.0.0` | Yes | High-throughput, low-footprint caching |
| Memory | (core) | in-process `dict` | Development / test | Local dev, unit tests, single-process apps |

Install extras: `pip install lexigram-cache[redis,memcached]`.

## Backend Details

### Redis

Full-featured distributed cache with replication, persistence, and pub/sub support.

- **Strengths:** High throughput, data persistence (RDB/AOF), atomic operations, built-in lock and rate-limit primitives. Supports `RedisStateStore`, `RedisLockStore`, and `RedisSecretStore` for distributed coordination. SSL/TLS, connection pooling, and socket timeouts are configurable.
- **Weaknesses:** External dependency — requires a running Redis server. Memory is bounded by the server's `maxmemory` setting.
- **When to choose:** Multi-service apps, session storage, rate limiting, distributed locking, or any production caching where cache durability matters.

```yaml
cache:
  backends:
    - name: primary
      type: redis
      default: true
      redis_host: localhost
      redis_port: 6379
      redis_db: 0
      default_ttl: 3600
      key_prefix: myapp
  service:
    enable_protection: true
    default_serializer: json
```

### Memcached

Lightweight, high-performance distributed memory cache.

- **Strengths:** Extremely fast, minimal overhead, simple protocol, predictable memory usage. Well-suited for read-heavy workloads where cache eviction is acceptable.
- **Weaknesses:** No persistence, no replication, no atomic operations beyond get/set/delete. Maximum key size of 250 bytes, value size capped at 1 MB. Cache stampede protection is handled at the service layer (not natively).
- **When to choose:** High-throughput read caches, API response caching, HTML fragment caching — workloads where losing a cache entry is harmless.

```yaml
cache:
  backends:
    - name: sessions
      type: memcached
      memcached_host: localhost
      memcached_port: 11211
      default_ttl: 1800
```

### Memory

Zero-dependency in-process cache backed by a `dict`. TTL eviction runs on a configurable `cleanup_interval`.

- **Strengths:** No external process, no install, instant setup. Perfect for testing and single-process apps. Supports `max_size` limits and periodic cleanup.
- **Weaknesses:** Data is process-local — lost on restart and invisible to other processes. Cannot scale horizontally.
- **When to choose:** Unit tests, CI pipelines, local development, single-process CLI tools.

```yaml
cache:
  backends:
    - name: dev
      type: memory
      default: true
      max_size: 10000
      cleanup_interval: 60
```

## Quick Selection Guide

- **I need a shared cache across processes/servers** → `redis`. Add `[redis]` extra.
- **I need the fastest possible read cache, and persistence doesn't matter** → `memcached`. Add `[memcached]` extra.
- **I'm writing unit tests** → `memory`. No extra needed.
- **I need distributed locks or state stores** → `redis`. Memory and Memcached don't support `RedisLockStore`/`RedisStateStore`.

## Multi-Backend Configuration

Multiple backends can coexist — each registered under its name for `Named` injection:

```yaml
cache:
  backends:
    - name: hot
      type: redis
      default: true
      redis_url: redis://localhost:6379/0
      default_ttl: 300
    - name: cold
      type: redis
      redis_url: redis://remote-host:6379/0
      default_ttl: 86400
    - name: local
      type: memory
      max_size: 500
```

Resolve by name:

```python
from typing import Annotated
from lexigram.contracts.infra.cache import CacheBackendProtocol
from lexigram.di.markers import Named

class MultiTierCache:
    def __init__(
        self,
        hot: Annotated[CacheBackendProtocol, Named("hot")],
        cold: Annotated[CacheBackendProtocol, Named("cold")],
    ):
        ...
```

## Stampede Protection

When `service.enable_protection` is `true`, the `CacheService` wraps the default backend in a `StampedeProtectedCache`. Only the first concurrent request computes the value — subsequent requests wait on a distributed lock.

```yaml
cache:
  service:
    enable_protection: true
    protection_lock_ttl: 5
    protection_max_wait: 2.0
```

Stampede protection requires the underlying backend to support locks, so it is only available with Redis.

## Serialization

Configured via `service.default_serializer` (default: `json`). Available options:

| Serializer | Class | Key features |
|------------|-------|--------------|
| `json` | `JSONSerializer` | Safe, cross-language, no extra deps |
| `pickle` | `PickleSerializer` | Supports arbitrary Python objects (opt-in) |
| `compression` | `CompressingSerializer` | Wraps another serializer with gzip/zlib |

## Testing

Use the memory backend for tests:

```python
from lexigram.cache import CacheConfig, CacheProvider

config = CacheConfig(
    backends=[
        CacheBackendConfig(name="test", type="memory", default=True, max_size=1000),
    ]
)
provider = CacheProvider(config)
```

Or use `FakeCache` from `lexigram-testing`:

```python
from lexigram.testing import FakeCache

cache = FakeCache()
```
