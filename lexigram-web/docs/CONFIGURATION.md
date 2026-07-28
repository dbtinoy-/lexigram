---
title: lexigram-web Configuration
description: Every configuration key for the web layer.
---

## Config Section

All web configuration lives under the `web` key in `application.yaml`. The provider auto-injects the typed `WebConfig` — no manual loading needed.

Env prefix: `LEX_WEB__` | Nested delimiter: `__`

```yaml
web:
  enabled: true
  env: development
  server:
    host: 0.0.0.0
    port: 8000
    workers: 1
    reload: false
    debug: false
  openapi_title: "My API"
  openapi_version: "1.0.0"
```

```bash
export LEX_WEB__SERVER__HOST=0.0.0.0
export LEX_WEB__SERVER__PORT=8080
```

---

## WebConfig

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `enabled` | `bool` | `True` | `LEX_WEB__ENABLED` | Enable the web module |
| `env` | `str \| None` | `None` | `LEX_WEB__ENV` | Environment name (development/staging/production) |
| `openapi_title` | `str` | `"API"` | `LEX_WEB__OPENAPI_TITLE` | OpenAPI title |
| `openapi_version` | `str` | `"1.0.0"` | `LEX_WEB__OPENAPI_VERSION` | OpenAPI version |
| `openapi_url` | `str \| None` | `"/openapi.json"` | `LEX_WEB__OPENAPI_URL` | OpenAPI schema path |
| `swagger_ui_url` | `str \| None` | `"/docs"` | `LEX_WEB__SWAGGER_UI_URL` | Swagger UI path |
| `redoc_url` | `str \| None` | `"/redoc"` | `LEX_WEB__REDOC_URL` | ReDoc path |
| `compression_enabled` | `bool` | `True` | `LEX_WEB__COMPRESSION_ENABLED` | Enable response compression |
| `template_directory` | `str` | `"templates"` | `LEX_WEB__TEMPLATE_DIRECTORY` | Jinja2 template directory |
| `debug_routes` | `bool` | `False` | `LEX_WEB__DEBUG_ROUTES` | Enable `/debug/*` endpoints |
| `debug_routes_token` | `SecretStr \| None` | `None` | `LEX_WEB__DEBUG_ROUTES_TOKEN` | Token for debug routes (X-Debug-Token header) |
| `enable_auth` | `bool` | `False` | `LEX_WEB__ENABLE_AUTH` | Enable built-in auth middleware |
| `enable_identity_resolution` | `bool` | `False` | `LEX_WEB__ENABLE_IDENTITY_RESOLUTION` | Resolve OAuth external IDs |
| `max_body_size` | `int \| None` | `10485760` (10 MiB) | `LEX_WEB__MAX_BODY_SIZE` | Max request body size (None = disabled) |
| `auth_exclude_paths` | `list[str]` | `["/health", "/health/", "/docs", "/redoc", "/openapi.json"]` | `LEX_WEB__AUTH_EXCLUDE_PATHS` | Paths excluded from auth |

---

## ServerConfig

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `host` | `str` | `"127.0.0.1"` | `LEX_WEB__SERVER__HOST` | Bind host |
| `port` | `int` | `8000` | `LEX_WEB__SERVER__PORT` | Bind port |
| `workers` | `int` | `1` | `LEX_WEB__SERVER__WORKERS` | Number of workers |
| `reload` | `bool` | `False` | `LEX_WEB__SERVER__RELOAD` | Enable auto-reload |
| `debug` | `bool` | `False` | `LEX_WEB__SERVER__DEBUG` | Enable debug mode |

---

## RateLimitConfig

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `enabled` | `bool` | `True` | `LEX_WEB__RATE_LIMIT__ENABLED` | Enable rate limiting |
| `default_limit` | `int` | `100` | `LEX_WEB__RATE_LIMIT__DEFAULT_LIMIT` | Max requests per window |
| `default_window` | `int` | `60` | `LEX_WEB__RATE_LIMIT__DEFAULT_WINDOW` | Window in seconds |
| `whitelist_ips` | `list[str]` | `[]` | `LEX_WEB__RATE_LIMIT__WHITELIST_IPS` | Exempt IPs |
| `storage_backend` | `str` | `"memory"` | `LEX_WEB__RATE_LIMIT__STORAGE_BACKEND` | Backend (memory/redis) |

### Rate Limit Rules

Per-path rules in `rules`:

```yaml
web:
  rate_limit:
    rules:
      "/api/auth/login":
        requests: 10
        window: 60
      "/api/health":
        requests: 1000
        window: 60
```

---

## StaticFileConfig

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `enabled` | `bool` | `False` | `LEX_WEB__STATIC__ENABLED` | Enable static file serving |
| `directory` | `str` | `"static"` | `LEX_WEB__STATIC__DIRECTORY` | Directory to serve |
| `prefix` | `str` | `"/static"` | `LEX_WEB__STATIC__PREFIX` | URL prefix |
| `html` | `bool` | `False` | `LEX_WEB__STATIC__HTML` | Serve HTML (SPA mode) |

---

## APIDocsConfig

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `enabled` | `bool` | `False` | `LEX_WEB__API_DOCS__ENABLED` | Enable API docs endpoints |
| `provider` | `str` | `"both"` | `LEX_WEB__API_DOCS__PROVIDER` | "swagger", "redoc", or "both" |

---

## CORSConfig

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `allowed_origins` | `list[str]` | `["http://localhost:3000", "http://localhost:8001"]` | `LEX_WEB__CORS__ALLOWED_ORIGINS` | Allowed origins |
| `allow_methods` | `list[str]` | `["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]` | `LEX_WEB__CORS__ALLOW_METHODS` | Allowed HTTP methods |

:::warning
In production, `LEX_WEB__CORS__ALLOWED_ORIGINS` must be set to specific origins — wildcard `*` is rejected with a validation error.
:::

---

## SecurityConfig

Sub-keys: `security.csrf`, `security.headers`, `security.hsts`, `security.csp`, `security.cross_origin`. Import the typed configs from `lexigram.web.security.config` for full field listings.

```yaml
web:
  security:
    csrf:
      enabled: true
      excluded_paths: ["/api/", "/health", "/metrics"]
    hsts:
      max_age: 31536000
      include_subdomains: true
```

---

## Application Example

```yaml
# application.yaml
web:
  enabled: true
  env: development
  server:
    host: 0.0.0.0
    port: 8000
    reload: true
  cors:
    allowed_origins:
      - "http://localhost:3000"
  rate_limit:
    enabled: true
    default_limit: 200
    default_window: 60
  openapi_title: "My API"
  openapi_version: "0.1.0"
```

Environment override equivalent:

```bash
export LEX_WEB__SERVER__HOST=0.0.0.0
export LEX_WEB__SERVER__PORT=8080
export LEX_WEB__CORS__ALLOWED_ORIGINS='["https://myapp.com"]'
export LEX_WEB__RATE_LIMIT__DEFAULT_LIMIT=500
```
