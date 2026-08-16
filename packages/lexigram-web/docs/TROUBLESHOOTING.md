---
title: lexigram-web Troubleshooting
description: Common errors, causes, and fixes.
---

## `ConfigurationError: debug_routes=True requires either debug_routes_token or a debug_routes_auth callback`

**Cause:** You set `debug_routes: true` in config without providing a token or auth callback.

**Fix:** Set `debug_routes_token` in config or pass `debug_routes_auth` to `WebProvider`:

```yaml
web:
  debug_routes: true
  debug_routes_token: "my-secret-token"
```

```python
WebProvider(debug_routes_auth=lambda req: req.headers.get("X-Admin") == "yes")
```

---

## `ValueError: CRITICAL SECURITY ERROR: Wildcard CORS origin '*' not allowed in PRODUCTION`

**Cause:** `cors.allowed_origins` contains `*` and `env` is `production`.

**Fix:** Set specific origins:

```bash
export LEX_WEB__SECURITY__CORS__ALLOWED_ORIGINS='["https://myapp.com"]'
```

---

## `RuntimeError: Starlette app not initialized`

**Cause:** You called `run_server()` before the provider was booted.

**Fix:** Ensure the application has started before calling `run_server`:

```python
async with Application.boot(name="my-app", providers=[WebProvider()]) as app:
    # app is started — safe to call run_server
    provider = await app.container.resolve(WebProvider)
    provider.run_server()
```

---

## `DependencyResolutionError: Failed to resolve dependency for parameter 'X'`

**Cause:** A controller constructor parameter type is not registered in the container.

**Fix:** Ensure the service is registered — either with `@singleton` or via a provider:

```python
from lexigram import singleton


@singleton
class MyService:
    ...
```

---

## Routes not found (404)

**Cause:** Controllers not discovered or not registered.

**Fix:** Check that auto-discovery targets the right package:

```python
# Correct — discovers all Controller subclasses in my_app.controllers
app.add_provider(WebProvider.auto_discover("my_app.controllers"))
```

Ensure controller files are imported (import the package in `create_app()`):

```python
import my_app.controllers  # ensures @get/@post decorators run
```

---

## `RateLimitError: Too Many Requests` (429)

**Cause:** Rate limit exceeded. Default is 100 requests per 60 seconds.

**Fix:** Increase limits or whitelist trusted IPs:

```yaml
web:
  rate_limit:
    default_limit: 1000
    default_window: 60
    whitelist_ips:
      - "10.0.0.0/8"
```

---

## OpenAPI docs returning 404

**Cause:** `api_docs.enabled` is `False` (default).

**Fix:**

```yaml
web:
  api_docs:
    enabled: true
```

---

## GraphQL or Auth integration not working

**Cause:** `enable_auth` is `False` (default) or GraphQL integration is not wired.

**Fix:**

```yaml
web:
  enable_auth: true
```

For GraphQL, add `lexigram-graphql` to your project and register `GraphQLProvider`:

```python
from lexigram.graphql import GraphQLProvider

app.add_provider(GraphQLProvider(schema=my_schema))
```

---

## Debug Tips

- Set `server.debug: true` in config for verbose error pages and exception filters.
- Check the provider registration order — `WebProvider` must be added to the `Application` before `start()`.
- Enable query logging for integrations: `export LEX_LOGGING__LEVEL=DEBUG`.
- Use `WebModule.stub()` in tests to avoid starting a real HTTP server.
