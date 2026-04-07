---
title: lexigram-tenancy Troubleshooting
description: Common errors, causes, and fixes
---

## Tenant not resolved

```
TenantResolutionError: Tenant resolution failed
```

**Cause:** All resolvers returned `None` — no header, JWT claim, subdomain, or path pattern matched.  
**Fix:** Check the resolvers list and each resolver's configuration. Verify the `x-tenant-id` header is being sent.

## Tenant not found

```python
TenantNotFoundError(tenant_id="tenant-abc")
```

**Cause:** The resolver extracted a tenant ID, but the store has no matching record.  
**Fix:** Verify the tenant was created via `TenantProviderProtocol.create_tenant()`. Check the store backend (in-memory is lost on restart).

## Tenant is inactive/suspended

```python
TenantInactiveError(tenant_id="tenant-abc")
TenantSuspendedError(tenant_id="tenant-abc")
```

**Cause:** The tenant exists but is not `ACTIVE`.  
**Fix:** Reactivate via `provider.activate_tenant(tenant_id)`. For suspended tenants, resolve the billing/compliance issue first.

## Middleware not firing

```
[no error — tenant not resolved]
```

**Cause:** `TenantContextMiddleware` was not registered, or `lexigram-web` is not installed.  
**Fix:** Verify `lexigram-web` is installed and the middleware registry is available. Check boot logs for `tenant_context_middleware_registered`.

## Schema isolation fails on tenant creation

```python
TenantProvisioningError: Tenant provisioning failed
```

**Cause:** The database user lacks `CREATE SCHEMA` permissions, or `lexigram-sql` is not installed.  
**Fix:** Grant schema creation permissions. Install `lexigram-tenancy[sql]`. Switch to row-level isolation as a temporary workaround.

## SQL bridge not working

```
[tenant context not available in SQL queries]
```

**Cause:** `IntegrationConfig.sql_context_bridge` is `False`, or `lexigram-sql` is not installed.  
**Fix:** Set `sql_context_bridge: true` in tenancy config. Verify `lexigram-sql` is installed.

## Tenant slug conflict on creation

```python
TenantSlugConflictError: Tenant slug 'acme-corp' already exists
```

**Cause:** A tenant with the same slug already exists in the store. Slug must be globally unique.

**Fix:** Use a unique slug, or append a discriminator:

```python
from lexigram.contracts.tenancy.protocols import TenantProviderProtocol

provider = await container.resolve(TenantProviderProtocol)
result = await provider.create_tenant(name="Acme Corp", slug="acme-corp")
if result.is_err() and isinstance(result.unwrap_err(), TenantSlugConflictError):
    result = await provider.create_tenant(name="Acme Corp", slug="acme-corp-2")
```

## Subdomain resolver returns None

**Symptom:** The subdomain resolver never extracts a tenant ID, even though requests come from `acme.app.com`.

**Cause:** `ResolutionConfig.subdomain_pattern` is `None` (default). The subdomain resolver requires a base domain pattern to extract the tenant subdomain.

**Fix:** Set the subdomain pattern in config:

```yaml
tenancy:
  resolution:
    subdomain_pattern: "app.com"
```

With `subdomain_pattern: "app.com"`, a request to `acme.app.com` extracts `acme` as the tenant ID.

## Tenant provisioning fails on isolation setup

```python
TenantProvisioningError: Tenant provisioning failed
```

**Cause:** The isolation strategy (`row_level` or `schema`) failed during `auto_provision_isolation`. Common causes: missing database permissions, or `lexigram-sql` not installed for schema-based isolation.

**Fix:** Check the provisioning logs and ensure the isolation prerequisites are met:

```bash
# For schema isolation, the database user needs CREATE SCHEMA
GRANT CREATE ON DATABASE mydb TO app_user;
```

Disable auto-provisioning if you handle isolation separately:

```yaml
tenancy:
  lifecycle:
    auto_provision_isolation: false
```

## Tenant config overrides not applying

**Symptom:** `TenantConfigProvider.get(tenant_id)` returns global config instead of tenant-specific overrides.

**Cause:** The tenant-specific config was never stored, or the cache TTL hasn't expired since the overrides were updated.

**Fix:** Verify overrides were saved:

```python
from lexigram.tenancy.config_overrides import TenantConfigService

store = await container.resolve(TenantConfigService)
await store.set_override(tenant_id, "features.premium", True)

# Clear cache to pick up changes
await store.clear_tenant_cache(tenant_id)
```

Lower the cache TTL in development:

```yaml
tenancy:
  overrides:
    cache_ttl: 5  # seconds (default is higher)
```
