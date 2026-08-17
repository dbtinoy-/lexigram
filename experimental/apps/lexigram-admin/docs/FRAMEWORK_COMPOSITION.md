# Framework Composition Map

## Three-Ring Architecture

```
  ┌────────────────────────────────────────────────────┐
  │ Ring 3 — App / Plugin code                         │
  │  - declares Resources, custom RowActions,          │
  │    PageDefinitions, widgets, settings panels       │
  │  - registers via BaseAdminContributor              │
  └────────────────────────────────────────────────────┘
              ↑ depends only on contracts
  ┌────────────────────────────────────────────────────┐
  │ Ring 2 — lexigram-admin                            │
  │  - Resource/Action/Page/Form/Table orchestration   │
  │  - DashboardAssembler, NavigationAssembler         │
  │  - AdminRenderer, AdminRouter, AdminBuilder        │
  │  - resource-scoped RBAC (field/action/record)      │
  │  - admin-specific UX (filter bar, command palette) │
  └────────────────────────────────────────────────────┘
              ↑ consumes
  ┌────────────────────────────────────────────────────┐
  │ Ring 1 — Framework packages (existing)             │
  │  lexigram-contracts ← all admin-facing protocols   │
  │  lexigram (core), lexigram-ui, lexigram-web        │
  │  lexigram-auth (identity, sessions, OAuth)         │
  │  lexigram-tenancy (tenant resolution, isolation)   │
  │  lexigram-monitor (metrics, health, observability) │
  │  lexigram-events (command/query/event buses)       │
  │  lexigram-cache, lexigram-tasks, lexigram-search,  │
  │  lexigram-resilience (OPTIONAL light-up)           │
  └────────────────────────────────────────────────────┘
```

Admin orchestrates; it does not implement identity, tenancy, or metrics.

## Required Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `lexigram` | ≥0.2 | DI container, `Provider`, `Module`, `Result` |
| `lexigram-contracts` | ≥0.2 | All admin-facing protocols, `BaseAdminContributor` |
| `lexigram-ui` | ≥0.2 | UI components: atoms, molecules, organisms |
| `lexigram-web` | ≥0.2 | ASGI / Starlette integration, `AdminRouter` |
| `lexigram-sql` | ≥0.2 | Database provider, data source protocol |
| `lexigram-events` | ≥0.2 | CQRS buses, domain events |

## Optional Integrations

| Integration | Package | Declarative knob | What it gives you |
|---|---|---|---|
| **Cache** | `lexigram-cache` | `Resource.cacheable = True` | `list()` results cached with TTL; invalidation on create/update/delete |
| **Tasks** | `lexigram-tasks` | `BulkAction.task_runner = "tasks"` | Bulk actions dispatched as background tasks; progress visible in admin UI |
| **Search** | `lexigram-search` | `Resource.searchable = True` | Resources indexed on create/update/delete; `?q=` uses framework search engine |
| **Resilience** | `lexigram-resilience` | `DataSource.resilient = True` | Data-source calls wrapped in retry + circuit-breaker |
| **Features** | `lexigram-features` | `AdminBuilder.feature(name)` | Feature-flag gating for admin sections |
| **Storage** | `lexigram-storage` | `FileField.storage = "s3"` | File uploads routed through framework storage backend |
| **Auth** | `lexigram-auth` | *(automatic when installed)* | Identity, sessions, JWT, OAuth delegated to framework |
| **Tenancy** | `lexigram-tenancy` | `AdminConfig.tenancy.enabled = True` | Multi-tenant resource scoping delegated to framework |
| **Monitor** | `lexigram-monitor` | *(automatic when installed)* | Metrics, health checks, structured logging delegated to framework |

## What Admin Does NOT Do For You

- **Identity, sessions, OAuth, JWT** — delegated to `lexigram-auth`. Admin keeps only resource-scoped RBAC (field/action/record-level permissions).
- **Tenant resolution and isolation** — delegated to `lexigram-tenancy`. Admin keeps only tenant-scoped resource query wrappers.
- **Metrics, health checks, tracing** — delegated to `lexigram-monitor`. Admin keeps only the dashboard health rollup widgets.
- **CQRS buses** — delegated to `lexigram-events`. Admin defines only the message marker classes.
