---
title: lexigram-web Security
description: Secure-by-default web configuration — CORS, CSRF, rate limiting, input sanitization, and security headers
---

## CORS Configuration

`CORSConfig` controls cross-origin resource sharing. Never use `*` in production with credentials.

```yaml
# application.yaml
web:
  cors:
    enabled: true
    allowed_origins:
      - "https://app.myapp.com"
      - "https://admin.myapp.com"
    allow_credentials: true
    allow_methods:
      - GET
      - POST
      - PUT
      - DELETE
      - PATCH
    expose_headers:
      - X-Request-Id
    max_age: 600
```

The `CORSConfig` validator rejects `allow_credentials=True` combined with `allowed_origins=['*']` — browsers block such responses.

```python
# ✅ Correct — explicit origins with credentials
config = CORSConfig(allowed_origins=["https://myapp.com"], allow_credentials=True)

# ❌ RuntimeError — browser-incompatible
config = CORSConfig(allowed_origins=["*"], allow_credentials=True)
```

In production, `WebConfig.validate_production_security()` blocks wildcard CORS at boot:

```yaml
# Raises ValueError at boot:
web:
  cors:
    allowed_origins: ["*"]
```

## CSRF Protection

CSRF protection is opt-in: `CSRFProtectionMiddleware` is added only when
`SecurityConfig.security.csrf.enabled` is `true` (default `false`). When
enabled, `csrf.secret_key` must be set — token generation and validation fail
closed (`ValueError`) without it.

```yaml
web:
  security:
    csrf:
      enabled: true
      cookie_name: csrf_token
      header_name: X-CSRF-Token
      cookie_secure: true        # HTTPS only
      cookie_httponly: true
      cookie_samesite: Lax
      token_length: 32
      token_ttl: 3600            # 1 hour
      excluded_paths:
        - /api/
        - /health
        - /metrics
```

The `CSRFProtectionMiddleware` sets a signed cookie on GET requests and validates the `X-CSRF-Token` header on state-changing methods (POST, PUT, DELETE, PATCH).

```python
from lexigram.web.security.csrf.protection import CSRFProtection

# Already registered by WebProvider.boot() — resolve from container
csrf: CSRFProtection = await container.resolve(CSRFProtection)
token = await csrf.generate_token()
# Set as X-CSRF-Token header on the client
```

## Rate Limiting

`RateLimitConfig` supports per-path rules with sliding window (Redis-backed) or fixed-window (cache-backed) algorithms:

```yaml
web:
  rate_limit:
    enabled: true
    default_limit: 100
    default_window: 60
    storage_backend: redis      # or "memory" (dev only)
    rules:
      "/api/auth/login":
        requests: 10
        window: 60
        burst: 5
      "/api/webhook":
        requests: 200
        window: 60
```

The `RateLimitMiddleware` operates per-IP by default. Use the `RateLimiter` directly for per-user limits:

```python
from lexigram.web.middleware.rate_limit import RateLimiter

limiter = RateLimiter(window=60, max_requests=30)
if await limiter.try_acquire(client_id="user:42"):
    # proceed
    pass
```

:::tip
Use `RateLimitProvider` to register a shared `CacheBackendProtocol`-backed limiter — this works across processes without Redis.
:::

## Input Sanitization

`InputSanitizationMiddleware` strips null bytes and rejects obvious script-injection patterns from query parameters before they reach controllers:

```python
from lexigram.web.middleware.sanitization import InputSanitizationMiddleware

# Added automatically when WebProvider is configured
# Sanitizes: null bytes, <script> tags, javascript: URIs
```

This is **defense-in-depth** — validate at the service layer too. The middleware does not inspect request bodies.

## Security Headers

`SecurityHeadersMiddleware` emits standard security headers with sensible defaults:

```yaml
web:
  security:
    hsts:
      enabled: true
      max_age: 31536000          # 1 year
      include_subdomains: true
      preload: false
    csp:
      enabled: true
      directives:
        default-src: "'self'"
        script-src: "'self'"
        style-src: "'self' 'unsafe-inline'"
        img-src: "'self' data: https: blob:"
        frame-ancestors: "'none'"
        base-uri: "'self'"
        form-action: "'self'"
    cross_origin:
      enabled: true
      opener_policy: same-origin
      embedder_policy: require-corp
```

Use `create_production_config()` for secure defaults or `create_development_config()` for local dev:

```python
from lexigram.web.middleware.security import (
    create_production_config,
    create_development_config,
)

production = create_production_config()   # strict HSTS, full CSP
development = create_development_config() # relaxed CSP, no HSTS
```

## Session Management

`SessionCookieBackend` stores session data in signed cookies (default) or server-side via a `SessionRepositoryProtocol` backend:

```yaml
web:
  security:
    session:
      cookie_name: session
      cookie_secure: true
      cookie_httponly: true
      cookie_samesite: Lax
      max_age: 86400             # 24 hours
```

## Error Response Hardening

lexigram-web never leaks internal tracebacks in production. The `DefaultExceptionFilter` returns sanitized error bodies:

```python
from lexigram.web.filters import DefaultExceptionFilter

# Debug mode includes stack traces; production strips them
filter = DefaultExceptionFilter(debug=False)
```

Custom error bodies use `ProblemDetail` (RFC 9457):

```python
from lexigram.web.errors.problem_detail import ProblemDetail

class MyError(HTTPError):
    def problem_detail(self) -> ProblemDetail:
        return ProblemDetail(
            type="https://docs.myapp.com/errors/rate-limit",
            title="Rate Limit Exceeded",
            status=429,
            detail="Too many requests. Retry after 30 seconds.",
        )
```

:::caution
**Common misconfiguration**: enabling `server.debug: true` in production. This exposes stack traces and disables security hardening. Set it to `false` (default) for production deployments.
:::
