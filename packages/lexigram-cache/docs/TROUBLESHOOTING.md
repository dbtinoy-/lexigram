---
title: lexigram-cache Troubleshooting
description: Common cache errors, their causes, and solutions
---

## `CacheConnectionError`: Cannot connect to Redis

**Exception:** `CacheConnectionError` (from `lexigram.cache.exceptions`)

**Cause:** The cache provider cannot establish a connection to the Redis server.

**Solution:**
1. Verify Redis is running: `redis-cli ping`
2. Check configuration:
```yaml
cache:
  backends:
    - name: "default"
      type: redis
      redis_host: "localhost"  # ← verify correct host
      redis_port: 6379         # ← verify correct port
```
3. For password-protected Redis, ensure `redis_password` is set
4. For SSL, verify `redis_ssl: true` and the correct certificate is available

## `CacheTimeoutError`: Cache operation timed out

**Exception:** `CacheTimeoutError` (from `lexigram.cache.exceptions`)

**Cause:** The backend operation exceeded the socket timeout.

**Solution:**
1. Check network connectivity between app and Redis/Memcached
2. Increase socket timeout:
```yaml
cache:
  backends:
    - name: "default"
      type: redis
      socket_timeout: 5.0  # default is 2.0
```
3. Check for network latency or firewall issues

## `CacheBackendError`: Backend operation failed

**Exception:** `CacheBackendError` (from `lexigram.cache.exceptions`)

**Cause:** The underlying storage backend returned an error (Redis command failed, Memcached server error).

**Solution:**
1. Check the backend service logs
2. Verify the backend is not overloaded
3. For Redis, check `maxmemory` and eviction policies: `redis-cli INFO memory`

## `CacheKeyError`: Invalid cache key

**Exception:** `CacheKeyError` (from `lexigram.cache.exceptions`)

**Cause:** A cache key is `None`, empty, or exceeds the backend's key length limit (Redis max: 512 MB, Memcached max: 250 bytes).

**Solution:**
1. Validate keys before passing to cache operations
2. Use `CacheKeyBuilderProtocol` for consistent key construction
3. Memcached: keep keys under 250 bytes

## `CacheSerializationError`: Serialization failure

**Exception:** `CacheSerializationError` (from `lexigram.cache.exceptions`)

**Cause:** The value cannot be serialized with the configured serializer.

**Solution:**
1. For JSON serializer, ensure all values are JSON-serializable (no `datetime`, `set`, custom objects)
2. For non-serializable objects, either:
   - Convert to a dict before caching
   - Register the value type in the deny-by-default type registry (`DEFAULT_REGISTRY`) for typed reconstruction
3. Use a custom `AsyncStringSerializerProtocol` implementation

## Default backend not found after configuration

**Cause:** Multiple or zero backends are marked as `default: true`.

**Solution:** Exactly one backend must have `default: true`:
```yaml
cache:
  backends:
    - name: "primary"
      type: memory
      default: true   # ← exactly one
    - name: "secondary"
      type: redis
      default: false  # ← not default
```

## Stampede protection not working

**Cause:** `service.enable_protection` is set to `false`, or the lock TTL is too short for the computation.

**Solution:**
```yaml
cache:
  service:
    enable_protection: true
    protection_lock_ttl: 60   # increase for expensive operations
    protection_max_wait: 30.0
```

## Cache miss on recently set value

**Cause:** The value was set on one backend but retrieved from a different named backend.

**Solution:** Verify you're using the same backend name for set and get:
```python
await cache.set("key", value, backend="fast")
value = await cache.get("key", backend="fast")  # use the same backend
```

Or use the default backend:
```python
await cache.set("key", value)   # uses default
value = await cache.get("key")  # also uses default
```

## `Insecure password` error in production

**Exception:** `ValueError` from `CacheConfig.validate_production_security()`

**Cause:** A Redis password like `"password"` or `"secret"` is used in production.

**Solution:** Set a strong Redis password:
```yaml
cache:
  backends:
    - name: "redis"
      type: redis
      redis_password: "${REDIS_PASSWORD}"  # use env var, not literal
```

## Debug Tips

- **Enable debug logging:** `export LOG_LEVEL=DEBUG` to see cache operations
- **Check health:** `health_check()` on `CacheProvider` returns per-backend status
- **Verify metrics:** `get_metrics()` on `CacheProvider` returns hit/miss/error counts
- **Test with memory backend:** Isolate cache issues by switching to in-memory:
  ```python
  module = CacheModule.stub()  # pure in-memory, no external deps
  ```
- **Check serializer:** Verify the value can round-trip through the configured serializer
