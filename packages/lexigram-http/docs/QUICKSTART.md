---
title: lexigram-http Quickstart
description: Install, configure, and make your first outbound HTTP request in under 5 minutes
---

Install the package:

```bash
uv add lexigram-http
```

## Minimal example (standalone)

```python
import asyncio
from lexigram.http import HTTPClient


async def main() -> None:
    async with HTTPClient.session_context() as client:
        response = await client.get("https://api.example.com/health")
        if response.ok:
            data = await response.json()
            print(f"Status: {data}")


asyncio.run(main())
```

## Via DI

```python
import asyncio
from lexigram import Application
from lexigram.http import HTTPModule


async def main() -> None:
    app = Application(name="my-app")
    app.add_module(HTTPModule.configure())
    async with Application.boot(name="my-app", modules=[HTTPModule.configure()]) as app:
        from lexigram.contracts.web import HTTPClientProtocol

        client = await app.container.resolve(HTTPClientProtocol)
        response = await client.get("https://api.example.com/health")
        if response.ok:
            print("API is healthy")


asyncio.run(main())
```

## What just happened

- `HTTPModule.configure()` registered `HTTPClient` as a container-managed singleton — bound to both `HTTPClient` and `HTTPClientProtocol`
- The connection pool was configured with defaults (10 max connections, 30s timeout, DNS cache TTL 300s)
- The resolved client made a GET request and returned an `HttpResponse`

## Next steps

- [Guide](./GUIDE.md) — connection pooling, interceptors, resilience, streaming
- [Architecture](./ARCHITECTURE.md) — provider, contracts, pool, retry, circuit breaker
- [Configuration](./CONFIGURATION.md) — pool config, proxy, timeouts, cookie jar
- [How-Tos](./HOWTOS.md) — custom headers, retry policy, streaming, base URL client
