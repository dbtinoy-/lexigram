---
title: lexigram-web Middleware
description: Middleware architecture, built-in middleware, custom middleware, and testing
---

## Architecture

lexigram-web's middleware follows the ASGI model — each middleware wraps the next in a chain:

```
Request → RequestBodySizeLimitMiddleware
        → WebHooksMiddleware
        → SecurityHeadersMiddleware
        → CORSMiddleware
        → CSRFProtectionMiddleware
        → RequestContextMiddleware
        → DIScopeMiddleware
        → (user middleware)
        → Router → Controller
```

Middleware is applied via `MiddlewareSetup.configure()` during `WebProvider.boot()`. The stack is composed once and frozen — it is never rebuilt per-request.

### Ordering

The `MiddlewareSetup` class applies middleware in security-first order:

1. **Auto-configure CSP** for API docs (mutates config for Swagger/ReDoc)
2. **Security headers** (HSTS, CSP, X-Frame-Options, cross-origin isolation)
3. **CORS** (cross-origin resource sharing)
4. **CSRF** (opt-in, configurable via `SecurityConfig.csrf`)
5. **Request context** (wires shared `Context` to the request scope)
6. **DI scope** (creates a request-scoped child container)
7. **Request body size limit** (protects against oversized payloads)
8. **Web hooks** (outermost — emits `WebRequestReceivedHook` / `WebResponsePreparedHook`)

User-supplied middleware is prepended to `DefaultMiddlewareStack.build()` before the internal stack, so it runs outermost.

## Built-in Middleware

| Middleware | Module | Purpose |
|-----------|--------|---------|
| `SecurityHeadersMiddleware` | `lexigram.web.middleware.security` | HSTS, CSP, X-Frame-Options, cross-origin isolation |
| `CORSMiddleware` | `lexigram.web.middleware.cors` | Cross-origin resource sharing |
| `CSRFProtectionMiddleware` | `lexigram.web.security.csrf.middleware` | CSRF token validation |
| `RateLimitMiddleware` | `lexigram.web.middleware.rate_limit` | Sliding-window rate limiting |
| `InputSanitizationMiddleware` | `lexigram.web.middleware.sanitization` | Strips null bytes and script injection from query params |
| `RequestBodySizeLimitMiddleware` | `lexigram.web.middleware.body_limit` | Enforces `max_body_size` (default 10 MiB) |
| `AccessLogMiddleware` | `lexigram.web.middleware.access_log` | Structured request logging |
| `RequestIDMiddleware` | `lexigram.web.middleware.request_id` | Generate and propagate `X-Request-Id` headers |
| `TimingMiddleware` | `lexigram.web.middleware.timing` | `X-Response-Time` header |
| `CompressionMiddleware` | `lexigram.web.middleware.compression` | Gzip/brotli response compression |
| `StaticFilesMiddleware` | `lexigram.web.middleware.static` | Serve static files |

## Custom Middleware

Write any ASGI callable — no base class required:

```python
from starlette.types import ASGIApp, Scope, Receive, Send


class RequestIDMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        scope["state"]["request_id"] = uuid.uuid4().hex
        await self.app(scope, receive, send)
```

### MiddlewareProtocol

For middleware that needs DI-resolved services, implement `MiddlewareProtocol` from `lexigram.web.middleware.base`:

```python
from lexigram.web.middleware import MiddlewareChain


class TimingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        import time
        start = time.perf_counter()
        await self.app(scope, receive, send)
        elapsed = time.perf_counter() - start
        # Send wrapper needed to inject response headers at the ASGI level
```

## Registering Middleware

### Via WebProvider

```python
from lexigram.web import WebProvider
from my_app.middleware import TimingMiddleware, RequestIDMiddleware

provider = WebProvider(
    middleware=[TimingMiddleware, RequestIDMiddleware],
)
```

### Via WebProvider.middleware_manager

```python
provider.middleware_manager.add(TimingMiddleware)
```

### Via WebConfig (entry-point discovery)

Packages can register middleware via the `lexigram.web.contributors` entry point. The `WebContributorRegistry` merges them at boot.

### Via application.yaml

Middleware configuration is driven by `WebConfig` fields — security headers, CORS, CSRF, rate limiting, body size, and static files are all configured declaratively:

```yaml
web:
  security:
    csrf:
      enabled: true
  cors:
    enabled: true
    allowed_origins: ["https://myapp.com"]
  rate_limit:
    enabled: true
    default_limit: 100
  max_body_size: 5242880  # 5 MiB
```

## Testing Middleware

Use `TestClient` from `lexigram.testing`:

```python
from lexigram.testing import WebTestClient
from lexigram.web import WebProvider


class TestRateLimitMiddleware:
    async def test_rate_limit_applied(
        self, test_client: TestClient, web_provider: WebProvider
    ) -> None:
        responses = await asyncio.gather(
            *[test_client.get("/api/test") for _ in range(110)]
        )
        last = responses[-1]
        assert last.status_code == 429  # Too Many Requests
        assert "Retry-After" in last.headers
```

### Testing custom middleware

```python
from starlette.testclient import TestClient
from lexigram.web.middleware.stack import DefaultMiddlewareStack


class TestRequestIDMiddleware:
    def test_request_id_added(self) -> None:
        stack = DefaultMiddlewareStack(
            extra_middlewares=[RequestIDMiddleware],
        )
        middlewares = stack.build()
        # Assert middleware is in the stack
        assert any(
            "RequestIDMiddleware" in str(mw.cls.__name__) for mw in middlewares
        )
```
