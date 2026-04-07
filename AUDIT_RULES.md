# AUDIT_RULES.md — Lexigram Framework Rules Audit

> **Source**: Static rule analysis for architectural boundaries, import policy, and package coverage.

---

## Severity Summary

| Severity | Count |
|----------|-------|
| critical | 9 |
| important | 30 |
| minor | 0 |

## Findings

| File | Line | Rule ID | Severity | Message |
|------|------|---------|----------|---------|
| `lexigram-admin/src/lexigram/admin/cache/adapter.py` | 14 | `no-cross-extension-import` | `critical` | lexigram-admin directly imports lexigram-cache via lexigram.cache.service.core; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-admin/src/lexigram/admin/cli/commands/search.py` | 85 | `no-cross-extension-import` | `critical` | lexigram-admin directly imports lexigram-search via lexigram.search.engine; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-admin/src/lexigram/admin/di/bundle_provider.py` | 605 | `no-cross-extension-import` | `critical` | lexigram-admin directly imports lexigram-search via lexigram.search.engine; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-admin/src/lexigram/admin/events/adapter.py` | 17 | `no-cross-extension-import` | `critical` | lexigram-admin directly imports lexigram-events via lexigram.events.buses.event; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-admin/src/lexigram/admin/events/adapter.py` | 18 | `no-cross-extension-import` | `critical` | lexigram-admin directly imports lexigram-events via lexigram.events.buses.event; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-admin/src/lexigram/admin/events/adapter.py` | 19 | `no-cross-extension-import` | `critical` | lexigram-admin directly imports lexigram-events via lexigram.events.messages.event; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-admin/src/lexigram/admin/integrations/search.py` | 90 | `no-cross-extension-import` | `critical` | lexigram-admin directly imports lexigram-search via lexigram.search.engine; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-admin/src/lexigram/admin/monitoring/adapter.py` | 17 | `no-cross-extension-import` | `critical` | lexigram-admin directly imports lexigram-monitor via lexigram.monitor.health.core; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-admin/src/lexigram/admin/monitoring/adapter.py` | 20 | `no-cross-extension-import` | `critical` | lexigram-admin directly imports lexigram-monitor via lexigram.monitor.types; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 65 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'UserCreated' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 73 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'UserUpdated' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 81 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'UserDeactivated' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 88 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'UserDeleted' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 95 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'ResourceCreated' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 105 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'ResourceUpdated' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 115 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'ResourceDeleted' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 125 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'BulkOperationCompleted' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 141 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'AdminEvent' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 148 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'ResourceRestored' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 156 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'ResourceViewed' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 164 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'ExportStarted' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 174 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'ExportCompleted' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 186 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'ExportFailed' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 195 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'ImportStarted' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 205 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'ImportCompleted' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 217 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'AdminUserLoggedIn' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 226 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'AdminUserLoggedOut' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 233 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'AdminUserCreated' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 243 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'AdminUserUpdated' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 251 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'PasswordChanged' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 258 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'RolesAssigned' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 267 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'ActionExecuted' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 278 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'SettingsUpdated' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 286 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'AdminStarted' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 294 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'AdminStopped' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 299 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'ConfigReloaded' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/integrations/__init__.py` | 19 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/integrations/__init__.py declares FunctionDef 'register' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/integrations/__init__.py` | 24 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/integrations/__init__.py declares FunctionDef 'get' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/navigation/__init__.py` | 10 | `import-absolute-only` | `important` | lexigram-admin/src/lexigram/admin/navigation/__init__.py uses a relative import; replace it with an absolute import. |

## Rule Diagnostics

| Rule ID | Severity | Findings | Detected Error About |
|---------|----------|----------|----------------------|
| `import-absolute-only` | `important` | 1 | Relative imports obscure package boundaries and are disallowed across the framework. |
| `init-no-logic` | `important` | 29 | __init__.py files should contain exports only so package entry points stay declarative. |
| `no-cross-extension-import` | `critical` | 9 | Core and extension packages must respect the declared dependency hierarchy instead of importing across forbidden boundaries. |

## Package Coverage

- Discovered packages: 43
- Covered packages: 43
- Missing packages: 0
- Coverage status: **PASS**

### Covered Packages

- `lexigram`
- `lexigram-admin`
- `lexigram-ai`
- `lexigram-ai-agents`
- `lexigram-ai-evaluation`
- `lexigram-ai-feedback`
- `lexigram-ai-governance`
- `lexigram-ai-guard`
- `lexigram-ai-llm`
- `lexigram-ai-mcp`
- `lexigram-ai-memory`
- `lexigram-ai-observability`
- `lexigram-ai-prompt`
- `lexigram-ai-rag`
- `lexigram-ai-session`
- `lexigram-ai-skills`
- `lexigram-ai-workers`
- `lexigram-audit`
- `lexigram-auth`
- `lexigram-cache`
- `lexigram-cli`
- `lexigram-contracts`
- `lexigram-events`
- `lexigram-features`
- `lexigram-graph`
- `lexigram-graphql`
- `lexigram-http`
- `lexigram-monitor`
- `lexigram-nosql`
- `lexigram-notification`
- `lexigram-queue`
- `lexigram-resilience`
- `lexigram-search`
- `lexigram-sql`
- `lexigram-storage`
- `lexigram-tasks`
- `lexigram-tenancy`
- `lexigram-testing`
- `lexigram-ui`
- `lexigram-vector`
- `lexigram-web`
- `lexigram-webhook`
- `lexigram-workflow`

### Missing Packages

- `(none)`

## Resolution Guide

- `import-absolute-only`: Replace relative imports (for example `from .module import ...`) with absolute imports rooted at `lexigram...` so module ownership stays explicit.
- `init-no-logic`: Keep `__init__.py` export-only. Move functions/classes to dedicated modules and re-export symbols through `__all__` from `__init__.py`.
- `no-cross-extension-import`: Move shared contracts to `lexigram-contracts`, register implementations via providers, and resolve dependencies through the container instead of direct extension imports.

