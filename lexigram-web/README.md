# lexigram-web

Web layer for Lexigram Framework — ASGI, routing, middleware, and API tooling.

---

## Overview

`lexigram-web` provides an ASP.NET Core-inspired HTTP layer built on Starlette with constructor injection, a `Result`-to-HTTP bridge that maps domain errors to status codes automatically, first-class middleware, guard, and filter pipelines, and OpenAPI docs auto-generation.

---


> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add lexigram lexigram-web[granian]

# With optional server backends
uv add "lexigram-web[uvicorn]"   # uvicorn
uv add "lexigram-web[hypercorn]"  # hypercorn
uv add "lexigram-web[security]"   # itsdangerous for signing
uv add "lexigram-web[templates]"  # Jinja2 template support
uv add "lexigram-web[websocket]"  # WebSocket support
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module
from lexigram.web import Controller, WebModule, WebProvider, get


class HelloController(Controller):
    @get("/hello")
    async def hello(self) -> dict[str, str]:
        return {"message": "Hello from Lexigram"}


@module(
    imports=[
        WebModule.configure(
            controllers=[HelloController],
            host="127.0.0.1",
            port=8000,
        )
    ]
)
class AppModule(Module):
    pass


async def main() -> None:
    async with Application.boot(modules=[AppModule]) as app:
        web = await app.container.resolve(WebProvider)
        web.run_server(host="127.0.0.1", port=8000)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Configuration

> **Zero-config usage:** Call `WebModule.configure()` with no arguments to use all defaults.

### Option 1 — YAML file

```yaml
# application.yaml
web:
  server:
    host: "0.0.0.0"
    port: 8000
    workers: 4
  cors:
    allowed_origins:
      - "https://app.example.com"
  rate_limit:
    enabled: true
    default_limit: "100/minute"
```

### Option 2 — Profiles + Environment Variables *(recommended)*

```bash
export LEX_WEB__SERVER__HOST=0.0.0.0
export LEX_WEB__SERVER__PORT=8080
export LEX_WEB__CORS__ALLOWED_ORIGINS='["https://app.example.com"]'
```

### Option 3 — Python

```python
from lexigram.web import WebModule
from lexigram.web.config import WebConfig, ServerConfig, RateLimitConfig

WebModule.configure(
    controllers=[UserController, OrderController],
    web_config=WebConfig(
        server=ServerConfig(host="0.0.0.0", port=8080, workers=4),
        rate_limit=RateLimitConfig(
            enabled=True,
            default_limit=200,
            default_window=60,
        ),
    ),
)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `server.host` | `"127.0.0.1"` | `LEX_WEB__SERVER__HOST` | Bind host |
| `server.port` | `8000` | `LEX_WEB__SERVER__PORT` | Bind port |
| `server.workers` | `1` | `LEX_WEB__SERVER__WORKERS` | Worker processes |
| `server.reload` | `False` | `LEX_WEB__SERVER__RELOAD` | Auto-reload on code change |
| `cors.allowed_origins` | `["localhost:3000", ...]` | `LEX_WEB__CORS__ALLOWED_ORIGINS` | CORS allow-list — wildcards blocked in production |
| `rate_limit.enabled` | `True` | `LEX_WEB__RATE_LIMIT__ENABLED` | Enable rate limiting |
| `rate_limit.default_limit` | `100` | `LEX_WEB__RATE_LIMIT__DEFAULT_LIMIT` | Requests per window |
| `rate_limit.default_window` | `60` | `LEX_WEB__RATE_LIMIT__DEFAULT_WINDOW` | Window in seconds |
| `rate_limit.storage_backend` | `"memory"` | `LEX_WEB__RATE_LIMIT__STORAGE_BACKEND` | `"memory"` or `"redis"` |
| `enable_auth` | `False` | `LEX_WEB__ENABLE_AUTH` | Enable built-in auth middleware |
| `api_docs.enabled` | `False` | `LEX_WEB__API_DOCS__ENABLED` | Enable `/docs` + `/redoc` |
| `max_body_size` | `10 MiB` | `LEX_WEB__MAX_BODY_SIZE` | Request body size limit |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `WebModule.configure(controllers, discover, ...)` | Configure with controllers and server settings |
| `WebModule.stub()` | No-op module for unit testing |

## Key Features

- **Controller pattern** — subclass `Controller` and annotate methods with HTTP decorators
- **Result-to-HTTP bridge** — `Result[T, DomainError]` maps automatically to status codes (404, 422, 403, etc.)
- **HTTP decorators** — `@get`, `@post`, `@put`, `@delete`, `@patch`, `@websocket`, etc.
- **Auto-discovery** — `WebModule.configure(discover=["my_app.api.v1"])`
- **Middleware pipeline** — register ASGI middleware via `AbstractMiddleware`
- **Exception filters** — `DefaultExceptionFilter` handles `DomainError` and `HTTPError` globally
- **Static files, API docs, debug routes** — configurable via `WebConfig`
- **Rate limiting** — per-path rules with memory or Redis storage backend
- **Security** — CORS wildcard blocked in production, CSRF enabled by default

## Testing

```python
from lexigram import Application
from lexigram.web import WebModule

async def test_controller():
    async with Application.boot(
        modules=[WebModule.stub()]
    ) as app:
        web = await app.container.resolve(WebProvider)
        assert web.starlette is not None
```

## Key Source Files

| File | What it contains |
|------|----------------|
| `src/lexigram/web/module.py` | `WebModule.configure()` |
| `src/lexigram/web/di/provider.py` | `WebProvider` boot phases |
| `src/lexigram/web/routing/decorators.py` | HTTP decorators (`@get`, `@post`, etc.) |
| `src/lexigram/web/routing/result_bridge.py` | `ResultResponseMapper` for Result-to-HTTP mapping |
| `src/lexigram/web/config.py` | `WebConfig`, `ServerConfig`, `RateLimitConfig` |
| `src/lexigram/web/middleware/__init__.py` | `AbstractMiddleware` base class |
| `src/lexigram/web/filters/__init__.py` | Exception filters |