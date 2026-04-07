---
title: "lexigram-cli CLI Matrix"
description: "Source-of-truth matrix documenting CLI entry points, commands, and lifecycle hooks across all Lexigram public packages."
---

# Public Package CLI Surface Matrix

Every public package in the Lexigram monorepo must have an explicit CLI
decision documented here.  The matrix is the source of truth for entry-point
expectations and is verified by boundary tests.

## Legend

| Column | Meaning |
|--------|---------|
| `entry_point` | exact `pyproject.toml` value or `none` |
| `root_commands` | root-level command names this package owns |
| `generators` | generator names this package owns |
| `health` | contributed health checks |
| `doctor` | contributed doctor checks |
| `shell` | contributed shell context |
| `hooks` | contributed CLI lifecycle hooks |
| `status` | `active` / `none` / `non-scope` |

## Matrix

### Packages WITH CLI Surface

| Package | Entry Point | Root Commands | Generators | Health | Doctor | Shell | Hooks | Status |
|---------|-------------|---------------|------------|--------|--------|-------|-------|--------|
| `lexigram-cli` (core) | `core = lexigram.cli.contributors.core:CoreCliContributor` | — | model, service, provider, event, test, command, query, guard | — | — | — | — | active |
| `lexigram-ai` | `ai = lexigram.ai.cli.contributor:AICliContributor` | ai | — | 2 (llm_provider, subsystem_discovery) | 1 (api_keys) | 1 (ai_client) | — | active |
| `lexigram-ai-mcp` | `mcp = lexigram.ai.mcp.cli.contributor:McpCliContributor` | mcp | mcp-controller, mcp-server | — | — | — | — | active |
| `lexigram-auth` | `auth = lexigram.auth.cli.contributor:AuthCliContributor` | auth | auth_guard, auth_policy | — | — | — | — | active |
| `lexigram-cache` | `cache = lexigram.cache.cli.contributor:CacheCliContributor` | cache | cache_repo | 1 | 1 | 1 | — | active |
| `lexigram-events` | `events = lexigram.events.cli.contributor:EventsCliContributor` | events | event_handler, saga | — | — | — | — | active |
| `lexigram-features` | `features = lexigram.features.cli.contributor:FeaturesCliContributor` | features | feature_flag | 1 | 1 | 1 | — | active |
| `lexigram-monitor` | `monitor = lexigram.monitor.cli.contributor:MonitorCliContributor` | monitor | metric | 2 | 2 | 1 | 1 | active |
| `lexigram-notification` | `notification = lexigram.notification.cli.contributor:NotificationCliContributor` | notify | notification_template | — | — | — | — | active |
| `lexigram-queue` | `queue = lexigram.queue.cli.contributor:QueueCliContributor` | — | message_consumer | — | — | — | — | active |
| `lexigram-search` | `search = lexigram.search.cli.contributor:SearchCliContributor` | — | search_index | — | — | — | — | active |
| `lexigram-sql` | `sql = lexigram.sql.cli.contributor:SqlCliContributor` | db | repository, filter, seeder, health | 1 | 2 | 2 | — | active |
| `lexigram-storage` | `storage = lexigram.storage.cli.contributor:StorageCliContributor` | — | storage_driver | 1 | 1 | — | — | active |
| `lexigram-tasks` | `tasks = lexigram.tasks.cli.contributor:TasksCliContributor` | tasks | task | — | — | — | — | active |
| `lexigram-tenancy` | `tenancy = lexigram.tenancy.cli.contributor:TenancyCliContributor` | tenancy | tenant_resolver | — | — | — | — | active |
| `lexigram-vector` | `vector = lexigram.vector.cli.contributor:VectorCliContributor` | vector | vector_collection | 1 | 1 | — | — | active |
| `lexigram-web` | `web = lexigram.web.cli.contributor:WebCliContributor` | — | controller, resource, middleware, graphql, webhook, websocket | — | 1 | — | — | active |
| `lexigram-workflow` | `workflow = lexigram.workflow.cli.contributor:WorkflowCliContributor` | workflow | workflow_def, pipeline, saga_step | 1 | — | 1 | — | active |
| `lexigram-audit` | `audit = lexigram.audit.cli.contributor:AuditCliContributor` | audit | — | 1 | 1 | — | — | active |
| `lexigram-graphql` | `graphql = lexigram.graphql.cli.contributor:GraphQLCliContributor` | — | dataloader | — | — | — | — | active |
| `lexigram-http` | `http = lexigram.http.cli.contributor:HttpCliContributor` | — | api_client | — | — | — | — | active |
| `lexigram-nosql` | `nosql = lexigram.nosql.cli.contributor:NoSqlCliContributor` | — | document_repo | — | — | — | — | active |
| `lexigram-resilience` | `resilience = lexigram.resilience.cli.contributor:ResilienceCliContributor` | — | — | 1 | 1 | 1 | — | active |

### Packages WITHOUT CLI Surface

| Package | Allowed Absence Reason | Status |
|---------|----------------------|--------|
| `lexigram` | Core framework runtime; CLI lives in `lexigram-cli`. No package-local CLI surface. | none |
| `lexigram-contracts` | Protocols, types, and exceptions only — no runtime CLI surface. | none |
| `lexigram-ai-llm` | CLI surface managed through `lexigram-ai` orchestrator. No standalone CLI. | none |
| `lexigram-ai-rag` | CLI surface managed through `lexigram-ai` orchestrator. No standalone CLI. | none |
| `lexigram-ai-agents` | CLI surface managed through `lexigram-ai` orchestrator. No standalone CLI. | none |
| `lexigram-ai-memory` | CLI surface managed through `lexigram-ai` orchestrator. No standalone CLI. | none |
| `lexigram-ai-skills` | CLI surface managed through `lexigram-ai` orchestrator. No standalone CLI. | none |
| `lexigram-ai-session` | CLI surface managed through `lexigram-ai` orchestrator. No standalone CLI. | none |
| `lexigram-ai-workers` | CLI surface managed through `lexigram-ai` orchestrator. No standalone CLI. | none |
| `lexigram-ai-observability` | CLI surface managed through `lexigram-ai` orchestrator. No standalone CLI. | none |
| `lexigram-ai-feedback` | CLI surface managed through `lexigram-ai` orchestrator. No standalone CLI. | none |
| `lexigram-graph` | No CLI surface yet. Graph DB operations are managed programmatically. | none |
| `lexigram-webhook` | No CLI surface yet. Webhook configuration is runtime-managed. | none |
| `lexigram-ui` | HTMX/htpy UI component library. No standalone CLI surface. | none |
| `lexigram-testing` | Pytest plugin and test utilities only. No CLI surface. | none |

## Conflict Policy

1. **Built-in commands** (registered in `lexigram-cli/src/.../runtime/main.py`) always win.
2. **Scope-dist contributors** (public packages listed above with status `active`) win over non-scope contributors for same command name.
3. **First-registered wins** for scope-vs-scope conflicts (stable by entry-point discovery order).
4. All conflicts are recorded in `LexigramRuntime.command_conflicts` and inspectable via `lexigram contrib list`.

## Verification

This matrix is verified by:

- `tests/scripts/test_cli_public_surface.py` — checks every public package has a documented CLI decision
- `lexigram-cli/tests/unit/test_cli_contribution_system.py` — verifies contributor registration
- `tools/publish_public.sh` — package list must agree with this matrix
