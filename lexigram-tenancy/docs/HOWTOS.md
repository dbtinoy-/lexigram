---
title: lexigram-tenancy How-Tos
description: Task-oriented recipes for common tenancy scenarios
---

## How do I resolve tenants from an HTTP header?

```python
from lexigram.tenancy import TenancyConfig, ResolutionConfig

config = TenancyConfig(
    resolution=ResolutionConfig(
        resolvers=["header"],
        header_name="x-tenant-id",
    ),
)
```

## How do I add a custom resolver?

```python
from lexigram.contracts.tenancy.protocols import TenantResolverProtocol
from lexigram.contracts.tenancy.types import TenantResolutionContext


class QueryParamResolver:
    """Resolves tenant from ?tenant_id=... query parameter."""

    name = "query_param"
    priority = 25

    async def resolve(self, context: TenantResolutionContext) -> str | None:
        return context.headers.get("x-query-tenant-id")
```

Register it by overriding `ResolverRegistry` in a custom provider.

## How do I use a SQL backend instead of in-memory?

Install with optional SQL support:

```bash
uv add lexigram-tenancy[sql]
```

Then register `SQLTenantProvider` before the lifecycle provider runs:

```python
from lexigram.tenancy.stores.sql import SQLTenantProvider

# Register before adding TenancyModule
container.singleton(TenantProviderProtocol, SQLTenantProvider(dsn=...))
```

## How do I configure per-tenant feature overrides?

```python
from lexigram.tenancy.config_overrides.service import TenantConfigService

service = await container.resolve(TenantConfigService)
await service.set_config("tenant-abc", "max_users", "100")
value = await service.get_config("tenant-abc", "max_users", default="10")
```

## How do I switch to schema-based isolation?

```python
from lexigram.tenancy import TenancyConfig, LifecycleConfig

config = TenancyConfig(
    lifecycle=LifecycleConfig(isolation_strategy="schema"),
)
```

Requires `lexigram-sql` and a Postgres database.

## How do I run a query scoped to the current tenant?

```python
from lexigram.primitives.context import TENANT_ID, Context

ctx = await container.resolve(Context)
tenant_id = ctx.get(TENANT_ID)
# Use tenant_id in SQL WHERE clause
```

## How do I use TenantGuard for route-level enforcement?

```python
from lexigram.tenancy import TenantGuard
from lexigram.web.controllers import use_guards

# Apply to a whole controller
@use_guards(TenantGuard)
class BillingController:
    async def list_invoices(self) -> list[Invoice]:
        ...

# Apply to a single route
class PublicController:
    @use_guards(TenantGuard)
    async def create_order(self, ...) -> Order:
        ...
```

The guard checks that a valid `ACTIVE` tenant is present in the current
request context. Requests without an active tenant receive a 403 response.

## How do I use TenantProvisioner for isolation setup?

```python
from lexigram.tenancy import TenantProvisioner
from lexigram.tenancy.isolation.row_level import RowLevelIsolationStrategy

strategy = RowLevelIsolationStrategy()
provisioner = TenantProvisioner(strategy=strategy, auto_provision=True)

# Provision isolation for a new tenant
result = await provisioner.provision("tenant-xyz")
if result.is_ok():
    print("Tenant schema/namespace provisioned")

# Deprovision when tenant is removed
await provisioner.deprovision("tenant-xyz")
```

Set `auto_provision=False` in tests to skip isolation setup entirely.

## How do I cache tenant config lookups?

```python
from lexigram.tenancy import CachedTenantConfigProvider
from lexigram.tenancy.stores.memory import InMemoryTenantProvider

base = InMemoryTenantProvider()
cached = CachedTenantConfigProvider(inner=base, ttl=60)

# First call fetches from the underlying provider
await cached.set_config("tenant-abc", "feature_x", "enabled")
value = await cached.get_config("tenant-abc", "feature_x")
print(value)  # "enabled"

# Subsequent reads within the TTL use the in-memory cache
cached_value = await cached.get_config("tenant-abc", "feature_x")

# Writes automatically invalidate the cache for that tenant
await cached.set_config("tenant-abc", "feature_x", "disabled")
```

The cache stores the entire config dict per tenant. A write to any key
invalidates that tenant's cached dict so the next read is fresh.

## How do I create a tenant programmatically?

```python
from lexigram.contracts.tenancy.protocols import TenantProviderProtocol
from lexigram.contracts.tenancy.commands import CreateTenantCommand

provider = await container.resolve(TenantProviderProtocol)
result = await provider.create_tenant(
    CreateTenantCommand(slug="newco", name="NewCo Inc.")
)
if result.is_ok():
    tenant = result.unwrap()
```
