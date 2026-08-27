# Spec: Multi-Tenant Notes

Slug `tenant-notes` · package `tenant_notes` · port 7087 (`TENANT_PORT`)
Subsystems: `lexigram-tenancy` (resolver chain, ASGI enforcement middleware, row-level isolation, tenant lifecycle, per-tenant config)

## Story

One notes app, three tenants (`acme`, `globex`, `initech`). Switch tenant via
header selector or path prefix and the note list hard-swaps — cross-tenant
reads are impossible by construction, not by filtering discipline. A red
"attempt violation" button fires a deliberately malformed request for another
tenant's note and displays the framework's rejection. An admin tab creates and
suspends tenants live, showing lifecycle events, and sets per-tenant config
(theme accent) that visibly restyles each tenant's workspace.

## Architecture

- **Resolver chain** demo order: `X-Tenant` header resolver first, then path
  prefix (`/t/{tenant}/...`) fallback — mirrors package's composable chain;
  ASGI enforcement middleware rejects unresolved/unknown tenants with 403.
- `NotesRepo` — row-level isolation strategy: repository scoped per tenant
  over an in-memory table (deterministic, no DB); tenant_id column enforced at
  repo layer (recon task pins tenancy's scoping seam so we use its protocol,
  not home-grown filtering).
- `TenantAdminService` — lifecycle CRUD through the package's service;
  domain events (created/suspended) surfaced in UI feed; suspended tenant
  requests fail closed.
- Per-tenant config overrides drive accent colour + locale label.

## Seeded state

Tenants acme/globex/initech each with 2–3 distinct notes; one suspended
tenant `skeleton` to show fail-closed.

## API

| Route | Purpose |
|---|---|
| `GET /api/notes` | current tenant's notes (resolver decides tenant) |
| `POST /api/notes {title, body}` | create in current tenant |
| `GET /api/notes/{id}` | 404 across tenants even with valid id from other tenant |
| `POST /api/violation {note_id}` | attempt cross-tenant read; returns framework error detail |
| `GET /api/admin/tenants` / `POST /api/admin/tenants {slug,name}` | lifecycle list/create |
| `POST /api/admin/tenants/{slug}/suspend` | suspend (fail-closed afterwards) |
| `PUT /api/admin/tenants/{slug}/config {accent}` | per-tenant override |

Header override honoured: any request may set `X-Tenant` (demo convenience).

## Console

Top bar: tenant switcher (header mode badge) + resolved-tenant chip + accent
swatch. Main: notes list/editor. Right rail tabs: Violation lab (button +
response viewer), Admin (tenants table, create form, suspend buttons, event
feed), Config (accent picker). Path-prefix mode link provided to compare
resolvers.

## Testing

Unit: resolver precedence header>path>reject; repo scope prevents cross-tenant
read/write even with raw ids; suspend blocks resolution; config override
affects preview payload only for that tenant. Integration: full CRUD under
header mode then identical ids under different tenant → 404; middleware 403
for unknown tenant; violation endpoint surfaces structured error. Console smoke.

## Non-goals

Schema/database isolation strategies (documented comparison table instead);
real auth for admin endpoints; billing/quota.
