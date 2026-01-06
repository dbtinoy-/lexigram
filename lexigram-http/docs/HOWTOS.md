---
title: lexigram-http How-Tos
description: Task-oriented recipes for common HTTP client scenarios
---

## How do I make a JSON POST request?

```python
result = await client.post(
    "https://api.example.com/users",
    json={"name": "Alice", "email": "alice@example.com"},
)
if result.is_ok():
    user = await result.unwrap().json()
```

## How do I add custom headers to every request?

```python
from lexigram.http.types import RequestContext


class AuthInterceptor:
    def __init__(self, token: str):
        self._token = token

    async def intercept_request(self, ctx: RequestContext) -> RequestContext:
        ctx.headers["Authorization"] = f"Bearer {self._token}"
        return ctx

    async def intercept_response(self, ctx: ResponseContext) -> ResponseContext:
        return ctx
```

## How do I configure retry with exponential backoff?

Retry requires `lexigram-resilience`:

```bash
uv add lexigram-resilience
```

```python
from lexigram.resilience.retry import RetryPolicy

policy = RetryPolicy(
    max_retries=3,
    base_delay=1.0,
    max_delay=30.0,
    retryable_statuses={429, 503},
)
```

The `HTTPProvider` automatically resolves` RetryPolicyProtocol` from the container at boot time.

## How do I stream a response body?

```python
async with client.session_context() as client:
    response = await client.get("https://api.example.com/large-file")
    if response.ok:
        async for chunk in response.stream():
            process_chunk(chunk)
```

## How do I use a base URL for all requests?

```python
from lexigram.http import BaseURLHTTPClient

client = BaseURLHTTPClient(
    inner=http_client,
    base_url="https://api.example.com",
)
user = await client.get("/users/42")  # → GET https://api.example.com/users/42
```

## How do I verify the connection pool health?

```python
from lexigram.http import HTTPProvider

provider = await container.resolve(HTTPProvider)
health = await provider.health_check()
print(health.status)  # HealthStatus.HEALTHY or UNHEALTHY
```

## How do I handle 4xx/5xx errors explicitly?

```python
result = await client.get("https://api.example.com/users/999")
result.match(
    ok=lambda resp: print(f"Success: {resp.status}"),
    err=lambda error: print(f"HTTP {error.status}: {error}"),
)

## How do I build a URL from parts?

```python
from lexigram.http import build_url, parse_url_parts

url = build_url(
    base="https://api.example.com",
    path="/users",
    params={"page": 1, "per_page": 50, "active": True},
)
# → "https://api.example.com/users?page=1&per_page=50&active=True"

parts = parse_url_parts(url)
# → {"scheme": "https", "host": "api.example.com", "port": None,
#     "path": "/users", "params": {"page": ["1"], "per_page": ["50"],
#     "active": ["True"]}, "fragment": ""}
```

## How do I use interceptors for cross-cutting concerns?

```python
from lexigram.http import InterceptorProtocol, RequestContext, ResponseContext


class LoggingInterceptor:
    async def intercept_request(self, ctx: RequestContext) -> RequestContext:
        print(f"→ {ctx.method} {ctx.url} (attempt {ctx.attempt})")
        return ctx

    async def intercept_response(self, ctx: ResponseContext) -> ResponseContext:
        status = ctx.status
        duration = ctx.duration
        print(f"← {status} ({duration:.2f}s)")
        return ctx


client = HTTPClient(
    config=config,
    interceptors=[LoggingInterceptor()],
)
```

## How do I configure connection pool limits?

```python
from lexigram.http.config import HTTPClientConfig, ConnectionPoolConfig

pool_config = ConnectionPoolConfig(
    max_connections=50,
    max_keepalive_connections=10,
    max_connections_per_host=20,
    timeout=60.0,
    ttl_dns_cache=600,
)

config = HTTPClientConfig(pool=pool_config)

client = HTTPClient(config=config)
```
