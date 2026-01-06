---
title: lexigram-tenancy Strategies
description: Isolation models, resolution strategies, configuration, migration, and testing
---

## Isolation Models

`lexigram-tenancy` provides three isolation strategies, each with a different tradeoff between isolation strength, operational cost, and complexity.

### Database-per-Tenant

Full database isolation. Each tenant gets a dedicated database.

```python
from lexigram.tenancy.isolation.database import DatabaseIsolationStrategy
```

| Dimension | Characteristic |
|-----------|---------------|
| **Isolation** | Strongest — full data separation |
| **Cost** | Highest — N databases to manage |
| **Complexity** | Connection routing per request |
| **Migration effort** | Highest — infra provisioning required |
| **Default in registry?** | No (reference implementation — must be subclassed) |
| **Provisioning** | `provision_isolation()` raises `NotImplementedError` — implement with RDS, Cloud SQL, etc. |

### Schema-per-Tenant

PostgreSQL schema isolation. Tenants share a database but are isolated at the schema level.

```python
from lexigram.tenancy.isolation.schema import SchemaIsolationStrategy
from lexigram.contracts.data import DatabaseProviderProtocol

asynccontextmanager
async def get_strategy(db: DatabaseProviderProtocol) -> SchemaIsolationStrategy:
    yield SchemaIsolationStrategy(db_provider=db, deprovision_policy="rename")
```

| Dimension | Characteristic |
|-----------|---------------|
| **Isolation** | Strong — PostgreSQL schema boundary |
| **Cost** | Moderate — single database, many schemas |
| **Complexity** | `search_path` routing via execution context |
| **Migration effort** | Requires `lexigram-tenancy[sql]` extra |
| **Default in registry?** | No (reference implementation — register explicitly) |

Deprovision policy options:

```python
# Archive the schema (rename to tenant_{id}_deprovisioned)
strategy = SchemaIsolationStrategy(db, deprovision_policy="rename")

# Permanently destroy the schema
strategy = SchemaIsolationStrategy(db, deprovision_policy="drop")
```

### Row-Level (Shared Table)

All tenants share the same tables. Data is disambiguated by a `tenant_id` column.

```python
from lexigram.tenancy.isolation.row_level import RowLevelIsolationStrategy
```

| Dimension | Characteristic |
|-----------|---------------|
| **Isolation** | Weakest — application-enforced |
| **Cost** | Lowest — single database, no schema overhead |
| **Complexity** | `tenant_id` in every query (handled by `lexigram-sql`'s `TenantScope`) |
| **Migration effort** | Minimal — add `tenant_id` to existing tables |
| **Default in registry?** | **Yes** — `IsolationStrategyRegistry.with_defaults()` includes it |

No provisioning required — `provision_isolation()` returns `Ok(None)`.

### Tradeoff Comparison

| Strategy | Isolation | Cost | Complexity | Provisioning | Recovery |
|----------|-----------|------|------------|--------------|----------|
| Database-per-tenant | ★★★★★ | $$$ | High | Custom infra code | Full DB restore |
| Schema-per-tenant | ★★★★ | $$ | Medium | `CREATE SCHEMA` | Schema restore |
| Row-level (default) | ★★ | $ | Low | None | Row-level backup |

## Resolution Strategies

Tenant resolution follows a configurable chain — resolvers are tried in priority order until one returns a tenant ID:

```yaml
# application.yaml
tenancy:
  resolution:
    resolvers:
      - jwt_claim          # priority: 10
      - header             # priority: 20
      - subdomain          # priority: 30
      - path               # priority: 40
```

### Available Resolvers

| Resolver | Name | Mechanism | Example |
|----------|------|-----------|---------|
| JWT Claim | `jwt_claim` | Decodes JWT, reads `tenant_id` claim | `{"sub": "...", "tenant_id": "acme"}` |
| Header | `header` | Reads HTTP header | `X-Tenant-Id: acme` |
| Subdomain | `subdomain` | Extracts from hostname | `acme.app.com` → `acme` |
| Path | `path` | Extracts from URL path | `/tenants/acme/users` → `acme` |

### Configuration per Resolver

```yaml
tenancy:
  resolution:
    resolver_names:
      - jwt_claim
      - header
    header_name: X-Tenant-Id
    subdomain_pattern: app.com        # acme.app.com → acme
    path_pattern: /tenants/{tenant_id}
    jwt_claim_key: tenant_id
    validator_cache_ttl: 300           # cache validated TenantInfo for 5 min
```

The `ResolverRegistry.from_config()` factory instantiates only the resolvers in `resolver_names`:

```python
from lexigram.tenancy.resolution.registry import ResolverRegistry

registry = ResolverRegistry.from_config(
    resolver_names=["jwt_claim", "header"],
    header_name="x-tenant-id",
    jwt_claim_key="tenant_id",
)
```

## TenantContextMiddleware

The `TenantContextMiddleware` runs on every HTTP request. It resolves the tenant, validates it, and sets `TENANT_ID` in the shared `Context`:

```python
from lexigram.tenancy import TenantContextMiddleware
from lexigram.primitives.context import TENANT_ID, Context

# After resolution, access the tenant in any service:
tenant_id = Context.get(TENANT_ID)
```

The middleware **never rejects** requests — it resolves the tenant if possible and sets `scope["state"]["tenant"]` for the optional `TenantGuard` to enforce later.

```python
from lexigram.tenancy import TenantGuard

# Applied per-route:
guard = TenantGuard()
result = await guard.authorize(request, required_tenant="acme")
```

## Migration Between Strategies

Migration from row-level → schema-per-tenant → database-per-tenant is incremental:

1. **Add the new strategy** to `IsolationStrategyRegistry` alongside the current one
2. **Dual-write** during a migration window
3. **Verify isolation** with the compliance suite
4. **Swap the default** in `LifecycleConfig.isolation_strategy`
5. **Deprovision the old strategy** after the migration window closes

```yaml
# During migration — both strategies active
tenancy:
  lifecycle:
    isolation_strategy: row_level   # current default
```

## Testing with Multi-Tenancy

```python
from lexigram.tenancy import InMemoryTenantProvider, TenancyProvider, TenancyConfig
from lexigram.tenancy.resolution.registry import ResolverRegistry
from lexigram.primitives.context import Context, TENANT_ID


class TestMultiTenantService:
    async def test_tenant_isolation(
        self, tenancy_provider: TenancyProvider
    ) -> None:
        # Set tenant context
        Context.get().set(TENANT_ID, "tenant-a")
        data_a = await service.query()

        Context.get().set(TENANT_ID, "tenant-b")
        data_b = await service.query()

        # Each tenant sees only their own data
        assert all(item.tenant_id == "tenant-a" for item in data_a)
        assert all(item.tenant_id == "tenant-b" for item in data_b)
```

Use `InMemoryTenantProvider` for test fixtures — it stores tenant records in-process.
