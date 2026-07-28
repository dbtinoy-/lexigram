---
title: "Multi-Tenancy"
description: "Tenant resolution, isolation, and enforcement with lexigram-tenancy."
---

`lexigram-tenancy` adds first-class multi-tenancy — identifying the current tenant, isolating its data, and propagating its context safely across async calls.

---

## 1. Three Pillars

1. **Resolution** — determine which tenant a request belongs to.
2. **Isolation** — separate tenant data (row, schema, or database).
3. **Enforcement** — bind the current context to the resolved tenant and reject requests that violate it.

---

## 2. Tenant Resolution

Resolution runs at the edge of the request pipeline. Resolvers are tried in order; the first match wins.

| Resolver | Source | Use case |
|----------|--------|----------|
| `header` | `X-Tenant-ID` header | API integrations, mobile apps |
| `jwt_claim` | a claim in the auth token | OAuth2 / OIDC requests |
| `subdomain` | `tenant.app.com` | classic SaaS |
| `path` | `/api/v1/{tenant}/...` | multi-org public portals |

```python
from lexigram import Application
from lexigram.tenancy import TenancyModule, TenancyConfig, ResolutionConfig

app = Application(name="my-saas")
app.add_module(
    TenancyModule.configure(
        TenancyConfig(resolution=ResolutionConfig(resolvers=["header", "jwt_claim"]))
    )
)
```

For tests, `TenancyModule.stub()` provides an in-memory, header-only setup with no isolation overhead.

---

## 3. Context Propagation

Once resolved, a `TenantContextMiddleware` stores the tenant id in a `ContextVar`, so it follows your code across `await` boundaries without being threaded through every function signature. Tenant-aware services and repositories read the current tenant from that context automatically.

See the [`lexigram-tenancy` package docs](/packages/lexigram-tenancy/) for the exact context-accessor and tenant-scoping decorator APIs.

---

## 4. Data Isolation Strategies

| Strategy | How | Trade-off |
|----------|-----|-----------|
| **Row-level** (shared table) | every row carries a `tenant_id` | cheapest; relies on consistent filtering |
| **Schema** (shared DB) | one Postgres schema per tenant | stronger isolation, moderate ops overhead |
| **Database** (separate DBs) | a database per tenant | strongest isolation; highest ops cost |

The isolation strategy is pluggable per tenant via the package's strategy registry.

:::caution
With **row-level** isolation, always rely on the tenant-aware repository layer so that every query is filtered by the current tenant — never hand-write unfiltered SQL across tenant tables.
:::

---

## 5. Enforcement

Mark routes as tenant-scoped so a request without a resolved, authorized tenant is rejected (`401` if no tenant is present, `403` if the user doesn't belong to it). The tenancy middleware validates the resolved tenant before the handler runs.

---

## Next Steps

- [Authentication](/guides/authentication/) — pairing tenants with JWT claims
- [Database & Persistence](/guides/database/) — tenant-aware repositories
- [`lexigram-tenancy` package](/packages/lexigram-tenancy/) — resolvers, isolation, and lifecycle
