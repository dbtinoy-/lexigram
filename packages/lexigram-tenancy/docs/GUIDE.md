---
title: lexigram-tenancy Guide
description: Mental model, core concepts, typical usage, and best practices for multi-tenancy
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `lexigram-sql` | Optional | Schema-per-tenant |
| `lexigram-cache` | Optional | Cached tenant config |

## Problem

Multi-tenant SaaS applications need to:

1. **Identify** which tenant owns each request
2. **Validate** the tenant is active and not suspended
3. **Isolate** tenant data at the database level
4. **Provide** per-tenant configuration overrides

Doing this ad-hoc leads to scattered tenant checks, inconsistent isolation, and subtle data leaks. `lexigram-tenancy` solves this with a declarative resolution chain, pluggable validation, and strategy-based isolation.

## Mental model

```
HTTP Request
    │
    ▼
[Resolution Chain] ── tries resolvers in priority order
    │                     header → subdomain → path → JWT claim
    ▼
[Tenant ID]  ──►  [Validator] ──► [Context TENANT_ID set]
                        │
                        ▼
              [Per-tenant config overrides]
                        │
                        ▼
              [Isolation Strategy]  ──►  row / schema / database level
```

Tenancy runs as ASGI middleware. Every request flows through resolution regardless of whether the route is tenant-scoped — the resolved `tenant_id` is set on `Context` and available to all downstream services.

## Core concepts

### Resolution chain

Resolvers are tried in priority order. The first to return a non-`None` tenant ID wins. Built-in resolvers:

| Resolver | Name | Priority | Reads |
|----------|------|----------|-------|
| JWT claim | `jwt_claim` | 10 | `scope["state"]["auth_claims"]["tenant_id"]` |
| Header | `header` | 20 | `X-Tenant-Id` HTTP header |
| Subdomain | `subdomain` | 30 | Host header (`acme.app.com` → `acme`) |
| Path | `path` | 40 | URL path (`/tenants/acme/...`) |

Configure order and naming via `ResolutionConfig.resolvers`.

### Validation

`TenantValidator` caches `TenantInfo` lookups and checks that the tenant is not `INACTIVE` or `SUSPENDED`. The resolution middleware never rejects — it resolves if possible and sets `scope["state"]["tenant"]` for downstream guards.

### Isolation strategies

| Strategy | `name` | How it works |
|----------|--------|--------------|
| Row-level | `row_level` | All tenants share tables; `tenant_id` column filters queries |
| Schema | `schema` | Each tenant gets a Postgres schema |
| Database | `database` | Each tenant gets a separate database |

Set via `LifecycleConfig.isolation_strategy`.

### Per-tenant config overrides

`TenantConfigService` provides a cached key-value overlay on top of `TenantConfigProviderProtocol`. Application config defaults are overridden per-tenant without code changes. Supports optional event bus integration for config change notifications.

## Typical usage

```python
from lexigram import Application
from lexigram.tenancy import (
    TenancyModule,
    TenancyConfig,
    ResolutionConfig,
    LifecycleConfig,
)

config = TenancyConfig(
    resolution=ResolutionConfig(
        resolvers=["header", "jwt_claim"],
        header_name="x-tenant-id",
    ),
    lifecycle=LifecycleConfig(
        isolation_strategy="row_level",
        auto_provision_isolation=True,
    ),
)

app = Application(name="my-app")
app.add_module(TenancyModule.configure(config=config))
```

## Integration with other packages

- **lexigram-web** — `TenantContextMiddleware` registers automatically as ASGI middleware when `lexigram-web` is present
- **lexigram-cache** — `TenantCacheKeyDecorator` prefixes cache keys with the active tenant ID (opt-in via `IntegrationConfig`)
- **lexigram-sql** — `TenantSQLContextBridge` syncs the tenant context into SQL scoped sessions (opt-in via `IntegrationConfig`)

## Best practices

- ✅ **Default to row-level isolation** — it's the simplest, most portable strategy
- ✅ **Use header resolution in production** — it's explicit and works with any client
- ✅ **Provide a JWT claim fallback** — for machine-to-machine auth where headers are insufficient
- ✅ **Set `auto_provision_isolation=True`** — isolation setup happens atomically with tenant creation
- ❌ **Don't rely on subdomain resolution in dev** — `localhost` has no meaningful subdomain
- ❌ **Don't resolve tenants in background workers** — there's no request context; use explicit tenant IDs instead
