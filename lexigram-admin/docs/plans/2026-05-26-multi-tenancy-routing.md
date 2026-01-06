# Multi-Tenancy-Aware Page Routing

**Goal:** Wire the existing multitenancy module into the admin's routing, middleware, and data access layers. When tenancy is enabled, requests get a resolved `tenant_id`, routes are optionally scoped by tenant, and data sources auto-filter by tenant.

## What Exists

- **`multitenancy/` module** — `TenantRegistry`, `TenantConfig`, `TenantScopedDataSource`, `get_tenant_id()`, `TenantProviderRegistry`, `resolve_tenant_id()`
- **`lexigram-contracts/tenancy/`** — richer `TenantResolverProtocol`, `TenantProviderProtocol`, `TenantInfo`, `TenantResolutionContext`
- **`AdminRouter`** — builds routes from resource registrations, supports `add_route()`
- **`AdminBundleProvider`** — orchestrates sub-providers, mounts middleware stack
- **No tenant config in `AdminConfig`** — tenancy isn't wired anywhere

## Plan

### Task A — Add tenancy config to `AdminConfig` (0.5 day)

Add `TenancyConfig` domain model to `config.py`:
- `enabled: bool = False`
- `tenant_field: str = "tenant_id"` — field name used for data filtering
- `resolution_order: list[str] = ["header", "cookie", "subdomain"]`
- `header_name: str = "x-tenant-id"`
- `cookie_name: str = "admin_tenant"`
- `route_prefix: str = ""` — if set to `"{tenant}"`, routes become `/{tenant}/users/`

### Task B — Create `TenancySubProvider` (1 day)

Create `lexigram-admin/src/lexigram/admin/di/sub_providers/tenancy.py`:
- Registers `TenantRegistry` as singleton
- Registers `TenantMiddleware` — resolves `tenant_id` per request, stores in `request.state.tenant_id`
- Wires `TenantScopedDataSource` wrapping for resources when tenancy is enabled
- Registered in `AdminBundleProvider` after `AdminCoreSubProvider`

### Task C — `TenantMiddleware` (0.5 day)

Create middleware that runs before auth:
- Calls `get_tenant_id(request)` to resolve tenant
- Sets `request.state.tenant_id` 
- If enabled and no tenant resolved for non-public routes, returns 403

### Task D — Wire data source scoping (0.5 day)

In `AdminBundleProvider.mount_to_app()`, after resolving resource data sources:
- If tenancy enabled, wrap each data source with `TenantScopedDataSource`

### Task E — Tests + CI (0.5 day)

Test the config, middleware integration, and data source wrapping end-to-end.

## ADR-009: Why not delegate to `lexigram-tenancy` yet

**Status:** Proposed

**Context:** Phase D.2 in `plans/2` plans full delegation to `lexigram-tenancy`, removing `TenantRegistry`/`TenantConfig` from admin. Doing that now would require the `lexigram-tenancy` package to be stable and fully available.

**Decision:** Wire the existing in-admin multitenancy module now. The migration to `lexigram-tenancy` is a separate task that replaces the backend, not the integration surface. `AdminConfig.tenancy` and `TenancySubProvider` are the stable integration surface — they will delegate to `lexigram-tenancy` after Phase D.2 but not change their API.
