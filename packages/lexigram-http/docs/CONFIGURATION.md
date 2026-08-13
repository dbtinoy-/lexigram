---
title: lexigram-http Configuration
description: Every configuration key for the HTTP client
---

Config section: `http`  
Env prefix: `LEX_HTTP__`  
Config model: `HTTPClientConfig`

## Top-level

| Key | Type | Default | Env var | Description |
|-----|------|---------|---------|-------------|
| `pool` | `ConnectionPoolConfig` | — | `LEX_HTTP__POOL__*` | Connection pool settings |
| `proxy` | `str \| None` | `None` | `LEX_HTTP__PROXY` | HTTP/HTTPS proxy URL |
| `trust_env` | `bool` | `True` | `LEX_HTTP__TRUST_ENV` | Read proxy from env vars |
| `cookie_jar` | `bool` | `True` | `LEX_HTTP__COOKIE_JAR` | Enable in-memory cookie jar |

## ConnectionPoolConfig

| Key | Type | Default | Env var | Description |
|-----|------|---------|---------|-------------|
| `max_connections` | `int` | `10` | `LEX_HTTP__POOL__MAX_CONNECTIONS` | Total concurrent connections |
| `max_keepalive_connections` | `int` | `5` | `LEX_HTTP__POOL__MAX_KEEPALIVE_CONNECTIONS` | Keep-alive per host |
| `max_connections_per_host` | `int` | `10` | `LEX_HTTP__POOL__MAX_CONNECTIONS_PER_HOST` | Max per host |
| `timeout` | `float` | `30.0` | `LEX_HTTP__POOL__TIMEOUT` | Request timeout (seconds) |
| `ttl_dns_cache` | `int` | `300` | `LEX_HTTP__POOL__TTL_DNS_CACHE` | DNS cache TTL (seconds) |
| `force_close` | `bool` | `False` | `LEX_HTTP__POOL__FORCE_CLOSE` | Force-close connections after use |

## Example YAML

```yaml
http:
  pool:
    max_connections: 50
    max_keepalive_connections: 20
    timeout: 10.0
    ttl_dns_cache: 60
  proxy: http://proxy.example.com:8080
  trust_env: true
  cookie_jar: true
```

Env var override form:

```bash
export LEX_HTTP__POOL__TIMEOUT=5.0
export LEX_HTTP__POOL__MAX_CONNECTIONS=100
export LEX_HTTP__PROXY=http://proxy.internal:8080
```
