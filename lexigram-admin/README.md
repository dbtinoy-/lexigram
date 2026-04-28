# lexigram-admin

Modern Python-first admin framework for Lexigram — HTMX, CRUD, dashboards, and extensions.

---

## Overview

Auto-generated admin panel for the Lexigram Framework. Provides CRUD interfaces,
bulk actions, role-based access, and audit logging for any domain model — with zero
frontend code required.

Built on `lexigram-ui` for responsive UI components and integrates with `lexigram-auth`
for RBAC permission enforcement. Configure via `AdminModule.configure()` and pass
`Resource` classes via the `resources=` argument.

## Install

```bash
uv add lexigram-admin
# Optional extras
uv add "lexigram-admin[auth,saml,ldap,oauth2,export]"
```

## Quick Start

```python
from lexigram import Application
from lexigram.admin import AdminModule
from lexigram.admin.config import AdminConfig
from lexigram.admin.resources.users import UserResource
from lexigram.sql import DatabaseModule
from lexigram.features import FeatureFlagsModule


async def main() -> None:
    async with Application.boot(
        modules=[
            DatabaseModule.configure(config="sqlite:///admin.db"),
            FeatureFlagsModule.configure(),
            AdminModule.configure(
                config=AdminConfig(title="My App Admin"),
                resources=[UserResource],
            ),
        ]
    ) as app:
        # ... admin panel served under /admin ...
        ...


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

> Resources are `Resource` subclasses (e.g. `UserResource`) passed to
> `AdminModule.configure(resources=[...])` — there is no global admin-site
> registry in `lexigram-admin`. The admin panel also requires a registered
> `DatabaseProviderProtocol` (here via `DatabaseModule` from `lexigram-sql`)
> and `FlagManagerProtocol` (via `FeatureFlagsModule`).

## Configuration

> **Zero-config usage:** Call `AdminModule.configure()` with no arguments to use defaults.

### Option 1 — YAML file

```yaml
# application.yaml
admin:
  prefix: /admin
  title: "My App Admin"
  features:
    audit_logging: true
```

### Option 2 — Profiles + Environment Variables *(recommended)*

```bash
export LEX_ADMIN__ENABLED=true
export LEX_ADMIN__TITLE="Production Admin"
```

### Option 3 — Python

```python
from lexigram.admin.config import AdminConfig

config = AdminConfig(
    prefix="/admin",
    title="My App Admin",
    features=AdminFeaturesConfig(audit_logging=True),
)
AdminModule.configure(config)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `prefix` | `/admin` | `LEX_ADMIN__PREFIX` | URL prefix for all admin routes |
| `title` | `Lexigram Admin` | `LEX_ADMIN__TITLE` | Panel title shown in browser and header |
| `auth.session_secret` | `change-me-in-production` | `LEX_ADMIN__AUTH__SESSION_SECRET` | Secret for signing session cookies (**required in production**) |
| `auth.session_lifetime` | `86400` | `LEX_ADMIN__AUTH__SESSION_LIFETIME` | Session validity in seconds (default: 24h) |
| `auth.idle_timeout` | `3600` | `LEX_ADMIN__AUTH__IDLE_TIMEOUT` | Idle session expiry in seconds |
| `features.audit_logging` | `true` | `LEX_ADMIN__FEATURES__AUDIT_LOGGING` | Log every write action with user and diff |
| `resource_defaults.per_page` | `20` | `LEX_ADMIN__RESOURCE_DEFAULTS__PER_PAGE` | Default rows per page |
| `ui.theme` | `system` | `LEX_ADMIN__UI__THEME` | UI colour scheme (`light`, `dark`, or `system`) |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `AdminModule.configure(...)` | Configure with explicit config, auth provider, resources, or controllers |
| `AdminModule.stub()` | Minimal config for testing |

## Key Features

- **Auto CRUD** — List, detail, create, edit, delete with zero boilerplate
- **Smart list** — Sortable columns, inline filters, pagination, search bar
- **Bulk actions** — Multi-select operations with progress and error summaries
- **Row actions** — Per-row buttons for custom single-object operations
- **Auth integration** — Plugs into `lexigram-auth` RBAC; per-model permission guards
- **Audit log** — Every write action logged with user, timestamp, diff
- **Change history** — Per-object change history with diff viewer
- **Password policy** — Configurable complexity rules for admin users
- **Custom pages** — `BaseAdminContributor.get_management_pages()` and `get_routes()` for bespoke views

## Testing

```python
from lexigram.admin import AdminModule
from lexigram.sql import DatabaseModule
from lexigram.features import FeatureFlagsModule

async with Application.boot(
    modules=[
        DatabaseModule.configure(config="sqlite:///test.db"),
        FeatureFlagsModule.configure(),
        AdminModule.stub(),
    ]
) as app:
    # your test code
    ...
```

> `AdminModule.stub()` still requires a `DatabaseProviderProtocol` and a `FlagManagerProtocol` binding (as in the Quick Start); it simply registers no resources or contributors.

## Key Source Files

| File | What it contains |
|------|-----------------|
| `src/lexigram/admin/module.py` | AdminModule definition with factory methods |
| `src/lexigram/admin/di/bundle_provider.py` | `AdminProvider` wiring |
| `src/lexigram/admin/config.py` | AdminConfig and all config sub-models |
| `src/lexigram/admin/contributors/` | Contributor registry, resource collection |

## Contributor System

`lexigram-admin` features a **plugin/contributor system** that lets third-party
packages extend the admin dashboard without modifying the host application.

Any package can become a contributor by:

1. Subclassing `BaseAdminContributor` from `lexigram-contracts`
2. Registering it via the `lexigram.admin.contributors` entry point group
3. Implementing methods like `get_resources()`, `get_dashboard_widgets()`,
   `get_navigation_items()`, `get_management_pages()`, `get_settings_panels()`,
   `get_routes()`, and `get_actions()`

Contributions are automatically namespaced by the contributor's `package_source`
to prevent name collisions. Collision behavior is configurable via
`AdminConfig.contributor_collision_mode` (`"warn"` | `"error"`).

For a complete walkthrough, see the [Extension Developer Guide](docs/EXTENSION_DEVELOPER_GUIDE.md).

### Example (plugin `pyproject.toml`)

```toml
[project.entry-points."lexigram.admin.contributors"]
my_plugin = "my_plugin.contributor:MyContributor"
```

## Operations

Production deployment guidance, rollback steps, audit-log backup/restore, session revocation, contributor triage, and metrics names live in [OPERATOR_RUNBOOK.md](./OPERATOR_RUNBOOK.md).
