# lexigram-http

Outbound HTTP client for the Lexigram Framework.

---

## Overview

Async outbound HTTP client for the Lexigram Framework. Provides a first-class
async HTTP client backed by `aiohttp`, with connection pooling, typed request/
response contexts, interceptor chains, base URL clients, streaming support, and
DI integration.

This package focuses on making **outbound** HTTP requests — for inbound web servers,
use `lexigram-web`. Resilience patterns (retry, circuit breaker) are layered in
through `lexigram-resilience`, not built in by default.


> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add lexigram-http
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module
from lexigram.http import HTTPModule, HTTPClientConfig

@module(imports=[HTTPModule.configure(HTTPClientConfig())])
class AppModule(Module):
    pass

async def main():
    async with Application.boot(modules=[AppModule]) as app:
        from lexigram.http import HTTPClient
        async with HTTPClient.session_context() as client:
            response = await client.get("https://api.example.com/users/123")
            if response.ok:
                user = await response.json()
                print(user)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Configuration

> **Zero-config usage:** Call `HTTPModule.configure()` with no arguments to use defaults.

### Option 1 — YAML file

```yaml
# application.yaml
http:
  pool:
    max_connections: 100
    max_keepalive_connections: 50
    timeout: 30.0
  trust_env: true
  cookie_jar: true
```

### Option 2 — Profiles + Environment Variables *(recommended)*

```bash
export LEX_HTTP__POOL__MAX_CONNECTIONS=100
export LEX_HTTP__POOL__TIMEOUT=30.0
export LEX_HTTP__TRUST_ENV=true
```

### Option 3 — Python

```python
from lexigram.http import HTTPModule, HTTPClientConfig, ConnectionPoolConfig

HTTPModule.configure(
    HTTPClientConfig(
        pool=ConnectionPoolConfig(
            max_connections=100,
            timeout=30.0,
        ),
        trust_env=True,
        cookie_jar=True,
    )
)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `pool.max_connections` | `10` | `LEX_HTTP__POOL__MAX_CONNECTIONS` | Total concurrent connections across all hosts |
| `pool.max_keepalive_connections` | `5` | `LEX_HTTP__POOL__MAX_KEEPALIVE_CONNECTIONS` | Keep-alive connections per host |
| `pool.max_connections_per_host` | `10` | `LEX_HTTP__POOL__MAX_CONNECTIONS_PER_HOST` | Max connections per individual host |
| `pool.timeout` | `30.0` | `LEX_HTTP__POOL__TIMEOUT` | Request timeout (seconds) |
| `pool.ttl_dns_cache` | `300` | `LEX_HTTP__POOL__TTL_DNS_CACHE` | DNS cache TTL (seconds) |
| `proxy` | `null` | `LEX_HTTP__PROXY` | HTTP/HTTPS proxy URL |
| `trust_env` | `True` | `LEX_HTTP__TRUST_ENV` | Read proxy settings from environment variables |
| `cookie_jar` | `True` | `LEX_HTTP__COOKIE_JAR` | Enable in-memory cookie jar |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `HTTPModule.configure(...)` | Configure with explicit HTTPClientConfig |
| `HTTPModule.stub()` | No-op HTTPModule for unit testing |

## Key Features

- **Connection pooling** — per-host limits, keepalive, DNS caching via aiohttp
- **Proxy support** — HTTP/HTTPS with environment variable auto-detection
- **Cookie jar** — optional, per-session in-memory cookie persistence
- **Streaming** — `StreamContext` for large file downloads
- **Interceptor chains** — composable auth, logging, metrics hooks
- **Type-safe contexts** — `RequestContext` and `ResponseContext` typed models

## Testing

```python
from lexigram.contracts.web import HTTPClientProtocol
from lexigram.http.types import ResponseContext

class FakeHTTPClient(HTTPClientProtocol):
    async def get(self, url: str, **kwargs) -> ResponseContext:
        return ResponseContext(status=200, headers={}, body=b'{"id": 123}')

# Inject into service under test
service = UserService(http_client=FakeHTTPClient())
```

## Key Source Files

| File | What it contains |
|------|-----------------|
| `src/lexigram/http/module.py` | HTTPModule with factory methods |
| `src/lexigram/http/config.py` | HTTPClientConfig and ConnectionPoolConfig |
| `src/lexigram/http/di/provider.py` | HTTPProvider — wires HTTP client into DI container |
| `src/lexigram/http/client/` | HTTPClient and BaseURLHTTPClient |
| `src/lexigram/http/pool/` | ConnectionPool (aiohttp connector abstraction) |
| `src/lexigram/http/types.py` | RequestContext and ResponseContext typed models |
