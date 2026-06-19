---
title: lexigram-cache Configuration
description: All configuration keys for cache — backends, service settings, and stampede protection
---

The configuration section key is **`cache`**. Values are read from YAML, environment variables (`LEX_CACHE__*`), or passed directly to `CacheConfig(...)`.

## Root: `CacheConfig`

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `enabled` | `bool` | `True` | `LEX_CACHE__ENABLED` | Enable caching |
| `version` | `str` | `"1.0.0"` | `LEX_CACHE__VERSION` | Config version |
| `environment` | `str` | `"development"` | `LEX_CACHE__ENVIRONMENT` | Runtime environment |
| `debug` | `bool` | `False` | `LEX_CACHE__DEBUG` | Debug mode |
| `backends` | `list[CacheBackendConfig]` | `[]` | — | Backend configurations |
| `service` | `CacheServiceConfig` | _(see below)_ | — | Service-level settings |

## `backends[]`: `CacheBackendConfig`

Common fields shared across all backend types:

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `name` | `str` | _(required)_ | — | Unique backend identifier |
| `type` | `BackendType` | _(required)_ | — | `memory`, `redis`, or `memcached` |
| `default` | `bool` | `False` | — | Exactly one backend must be default |
| `enabled` | `bool` | `True` | — | Enable this backend |
| `default_ttl` | `int` | `None` | — | Default TTL in seconds |
| `key_prefix` | `str` | `""` | — | Key prefix for namespace isolation |

### Memory-specific Fields

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `max_size` | `int` | `None` | Max entries before eviction |
| `cleanup_interval` | `int` | `300` | Cleanup interval in seconds |
| `enable_metrics` | `bool` | `True` | Enable metrics collection |

### Redis-specific Fields

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `redis_host` | `str` | `"localhost"` | `LEX_CACHE__BACKENDS__0__REDIS_HOST` | Redis host |
| `redis_port` | `int` | `6379` | `LEX_CACHE__BACKENDS__0__REDIS_PORT` | Redis port |
| `redis_db` | `int` | `0` | `LEX_CACHE__BACKENDS__0__REDIS_DB` | Redis database |
| `redis_password` | `str` | `None` | `LEX_CACHE__BACKENDS__0__REDIS_PASSWORD` | Redis password |
| `redis_url` | `str` | `None` | `LEX_CACHE__BACKENDS__0__REDIS_URL` | Full Redis URL |
| `redis_ssl` | `bool` | `False` | `LEX_CACHE__BACKENDS__0__REDIS_SSL` | Enable SSL/TLS |
| `redis_pool_size` | `int` | `10` | `LEX_CACHE__BACKENDS__0__REDIS_POOL_SIZE` | Connection pool size |

### Memcached-specific Fields

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `memcached_host` | `str` | `"localhost"` | — | Memcached host |
| `memcached_port` | `int` | `11211` | — | Memcached port |
| `memcached_servers` | `list[str]` | `None` | — | Server list (host:port) |

## `service`: `CacheServiceConfig`

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `enable_protection` | `bool` | `True` | `LEX_CACHE__SERVICE__ENABLE_PROTECTION` | Stampede protection |
| `enable_metrics` | `bool` | `True` | `LEX_CACHE__SERVICE__ENABLE_METRICS` | Service-level metrics |
| `enable_health_checks` | `bool` | `True` | `LEX_CACHE__SERVICE__ENABLE_HEALTH_CHECKS` | Health checks |
| `protection_lock_ttl` | `int` | `30` | `LEX_CACHE__SERVICE__PROTECTION_LOCK_TTL` | Lock TTL (seconds) |
| `protection_max_wait` | `float` | `10.0` | `LEX_CACHE__SERVICE__PROTECTION_MAX_WAIT` | Max lock wait |
| `protection_retry_interval` | `float` | `0.1` | `LEX_CACHE__SERVICE__PROTECTION_RETRY_INTERVAL` | Lock retry interval |
| `default_backend` | `str` | `None` | `LEX_CACHE__SERVICE__DEFAULT_BACKEND` | Default backend name |
| `circuit_breaker_enabled` | `bool` | `False` | `LEX_CACHE__SERVICE__CIRCUIT_BREAKER_ENABLED` | Circuit breaker |
| `circuit_breaker_threshold` | `int` | `5` | `LEX_CACHE__SERVICE__CIRCUIT_BREAKER_THRESHOLD` | Failure threshold |
| `default_serializer` | `str` | `"json"` | `LEX_CACHE__SERVICE__DEFAULT_SERIALIZER` | Serializer type |

## YAML Example

```yaml
cache:
  backends:
    - name: "hot"
      type: memory
      default: true
      max_size: 10000
      default_ttl: 300
    - name: "persistent"
      type: redis
      host: "${REDIS_HOST}"
      port: 6379
      redis_password: "${REDIS_PASSWORD}"
      redis_ssl: true
      key_prefix: "myapp"
      default_ttl: 3600
    - name: "fast"
      type: memcached
      host: "${MEMCACHED_HOST}"
      port: 11211
      default_ttl: 60

  service:
    enable_protection: true
    protection_lock_ttl: 30
    protection_max_wait: 10.0
    default_serializer: "json"
    allow_pickle: false
```

## Environment Variables

```bash
# Backend list (indexed by _0_, _1_, etc.)
export LEX_CACHE__BACKENDS__0__NAME="hot"
export LEX_CACHE__BACKENDS__0__TYPE="memory"
export LEX_CACHE__BACKENDS__0__DEFAULT=true
export LEX_CACHE__BACKENDS__1__NAME="persistent"
export LEX_CACHE__BACKENDS__1__TYPE="redis"
export LEX_CACHE__BACKENDS__1__REDIS_HOST="redis.example.com"
export LEX_CACHE__BACKENDS__1__REDIS_PORT=6379
export LEX_CACHE__BACKENDS__1__REDIS_PASSWORD="${REDIS_PASSWORD}"

# Service settings
export LEX_CACHE__SERVICE__ENABLE_PROTECTION=true
export LEX_CACHE__SERVICE__DEFAULT_SERIALIZER="json"

# Top-level
export LEX_CACHE__ENABLED=true
export LEX_CACHE__ENVIRONMENT="production"
```
