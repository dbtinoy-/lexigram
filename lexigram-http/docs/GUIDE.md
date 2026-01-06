---
title: lexigram-http Guide
description: Mental model, core concepts, typical usage, and best practices for outbound HTTP
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |

## Problem

Making HTTP requests in an async Python application requires connection pooling, timeout management, retry logic, and observability. Doing this correctly with raw `aiohttp` means wiring retries, circuit breakers, DNS caching, and error handling in every service. `lexigram-http` provides a first-class async HTTP client with built-in resilience, interception, and DI integration.

## Mental model

```
Application code
    │
    ▼
HTTPClient ──► InterceptorChain ──► ConnectionPool ──► Remote
    │              │                      │
    ├── get()      ├── RequestInterceptor  ├── max_connections
    ├── post()     ├── ResponseInterceptor ├── keepalive
    ├── put()      └── ...                 └── DNS cache
    ├── delete()
    ├── patch()
    └── request(verb, url)
                  │
                  ▼
              Result[HttpResponse, HTTPStatusError]
                  or
              HttpResponse (raw)
```

## Core concepts

### Client API

```python
from lexigram.http import HTTPClient

async with HTTPClient.session_context() as client:
    # Verb methods (return Result)
    result = await client.get("https://api.example.com/users")
    if result.is_ok():
        users = await result.unwrap().json()

    # With body
    result = await client.post(
        "https://api.example.com/users",
        json={"name": "Alice"},
    )

    # Raw request (returns HttpResponse directly)
    response = await client.request("GET", "https://api.example.com/health")
    if response.ok:
        data = await response.json()
```

### Connection pooling

The pool manages concurrent connections, keep-alive, and DNS caching:

| Setting | Default | Description |
|---------|---------|-------------|
| `max_connections` | 10 | Total concurrent connections |
| `max_keepalive_connections` | 5 | Keep-alive connections per host |
| `max_connections_per_host` | 10 | Max per individual host |
| `timeout` | 30s | Request timeout |
| `ttl_dns_cache` | 300s | DNS resolution cache TTL |

### Interceptors

Interceptors let you inspect and modify requests and responses:

```python
from lexigram.http import InterceptorProtocol
from lexigram.http.types import RequestContext, ResponseContext


class LoggingInterceptor:
    async def intercept_request(self, ctx: RequestContext) -> RequestContext:
        logger.info("http_request", method=ctx.method, url=ctx.url)
        return ctx

    async def intercept_response(self, ctx: ResponseContext) -> ResponseContext:
        logger.info("http_response", status=ctx.status, duration=ctx.duration)
        return ctx
```

### Resilience integration

When `lexigram-resilience` is registered, the HTTP client automatically wires:

- **Retry policy** — configurable backoff, max attempts, retryable status codes
- **Circuit breaker** — prevents cascading failures to unhealthy backends
- **Resilience pipeline** — combined retry + circuit breaker

## Typical usage

```python
from lexigram.http import HTTPClientConfig, ConnectionPoolConfig

config = HTTPClientConfig(
    pool=ConnectionPoolConfig(
        max_connections=50,
        timeout=10.0,
    ),
    trust_env=True,
)

app.add_module(HTTPModule.configure(config=config))
```

## Best practices

- ✅ **Use verb methods (`get()`, `post()`) for Result-based error handling** — explicitly handle 4xx/5xx vs transport errors
- ✅ **Reuse the same client via DI** — connection pooling is most effective with a shared pool
- ✅ **Set conservative timeouts** — start with 10s and tune up based on backend SLAs
- ✅ **Use `trust_env: true` in proxy-aware environments** — respects `HTTP_PROXY` / `HTTPS_PROXY`
- ❌ **Don't create a new `HTTPClient` per request** — that defeats connection pooling
- ❌ **Don't use raw `request()` when you need error handling** — use verb methods that return `Result`
