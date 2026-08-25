# LOC Debt Register

Files accepted as permanently over the 500-line LOC limit. Each entry
explains why decomposition would not improve maintainability.

Coverage: every `dev/loc_limit_baseline.txt` entry is documented either
here or, for the admin app, in the package-local register
(`experimental/apps/lexigram-admin/docs/loc_debt.md`, 14 files) — see
the Admin App section below.

## AI Extensions (Task 14 — W4 triage)

| File | Lines | Rationale |
|------|-------|-----------|
| `lexigram-ai-agents/.../plan_execute.py` | 526 | Already delegates to `_executor`, `_planner`, `_types` modules — thin orchestration wrapper |
| `lexigram-ai-governance/.../tracker.py` | 505 | Budget tracker with sliding-window counters and threshold alerting — self-contained enforcement logic |
| `lexigram-ai-governance/.../reservations.py` | 555 | Admission control across six scope dimensions — atomic reservation logic with sliding windows |
| `lexigram-ai-llm/.../aws_bedrock.py` | 592 | Transport adapter for Bedrock Converse API — single-responsibility provider client |
| `lexigram-ai-llm/.../pricing/sources.py` | 538 | Four pricing source implementations sharing common error handling |
| `lexigram-ai-llm/.../registry/core.py` | 583 | Provider registry with 14 built-in providers — registration data is inherently verbose |
| `lexigram-ai-llm/.../security/core.py` | 547 | Prompt injection protection — detection layers + sanitization + rate limiting |
| `lexigram-ai-llm/.../streaming/stream.py` | 511 | Streaming adapters + orchestrator + response aggregation |
| `lexigram-ai-llm/.../typed_responses.py` | 515 | Response type adapters (text, JSON, function call, structured, audio) |
| `lexigram-ai-mcp/.../di/provider.py` | 545 | MCP DI provider — wiring controllers, connectors, handlers, transports, client |
| `lexigram-ai-rag/.../loaders/core.py` | 539 | Document loaders (text, PDF, markdown, HTML, JSON, CSV) — each loader is 40–90 LOC |
| `lexigram-ai-relay-gateway/.../passthrough_service.py` | 583 | Passthrough relay — channel selection, billing, upstream transport, settlement |
| `lexigram-ai-workers/.../dlq/worker.py` | 540 | DLQ worker — error classification, retry with backoff, notification, health check |

## Auth Addendum

| File | Lines | Rationale |
|------|-------|-----------|
| `lexigram-auth/.../authn/_jwt_lifecycle.py` | 519 | JWT verify/refresh/revoke lifecycle mixin — barely over; seam exists but deferred to next wave (foreign-lane file that had never been baselined). |

## Rules

- New violations fail CI; entries whose files drop under the limit become
  stale and must be removed in the same change.
- Regenerate: `uv run python dev/check_loc_limit.py --root . --write-baseline`

## Extension Packages (Task 13 — W4 triage)

| File | Lines | Rationale |
|------|-------|-----------|
| `lexigram-auth/.../authn/ldap.py` | 509 | LDAP auth manager — cohesive single-backend authenticator with connection pooling, search, and bind |
| `lexigram-auth/.../authn/oauth2.py` | 560 | OAuth2 authenticator — token exchange, session management, multiple grant types tightly coupled |
| `lexigram-events/.../decorators/validation.py` | 530 | CQRS validation decorators — sync/async duplication is inherent to the decorator pattern |
| `lexigram-resilience/.../circuit/breaker.py` | 509 | Circuit breaker + registry — cohesive protection pattern, thin delegation |
| `lexigram-resilience/.../decorators.py` | 572 | Bulkhead/circuit/retry/timeout decorators — cohesive decorator module with shared retry logic |
| `lexigram-search/.../elasticsearch/backend.py` | 602 | Elasticsearch backend — transport adapter with search, bulk, index management, health check |
| `lexigram-sql/.../backup/backup_manager.py` | 542 | Backup/restore/validate/maintenance — cohesive backup lifecycle manager |
| `lexigram-sql/.../migrations/generator.py` | 520 | Migration generation — ModelAnalyzer + MigrationGenerator tightly coupled to schema diff |
| `lexigram-sql/.../migrations/manager/_alembic.py` | 503 | Alembic wrapper — vendored adapter, thin delegation layer |
| `lexigram-sql/.../schema/model.py` | 590 | Declarative schema model — ORM-like system with type mapping, constraints, indexes |
| `lexigram-storage/.../backends/azure.py` | 515 | Azure Blob storage driver — transport adapter |
| `lexigram-storage/.../backends/s3.py` | 506 | S3 storage driver — transport adapter |
| `lexigram-tasks/.../concurrency/compute.py` | 510 | ProcessPool with adaptive sizing — cohesive concurrency primitive |
| `lexigram-tasks/.../execution/worker.py` | 553 | TaskWorker — worker loop with middleware, retry, DLQ, idempotency (DI resolver extracted) |
| `lexigram-tasks/.../workflows/core.py` | 502 | Workflow composition — just barely over, cohesive orchestration |
| `lexigram-testing/.../auth/fixtures.py` | 568 | Auth test fixtures — test helpers, not production code |
| `lexigram-testing/.../cache/fixtures.py` | 508 | Cache test fixtures — test helpers |
| `lexigram-testing/.../events/fixtures.py` | 644 | Events test fixtures — test helpers |
| `lexigram-vector/.../search/reranking.py` | 536 | Reranking strategies — cohesive search component |
| `lexigram-web/.../di/provider.py` | 584 | WebProvider DI — large but cohesive registration of routes, middleware, error handlers |
| `lexigram-web/.../errors/html_error_renderer.py` | 540 | Debug HTML error renderer — template-heavy, cohesive UI component |
| `lexigram-web/.../middleware/rate_limit.py` | 588 | Rate limiting middleware — sliding window + token bucket + fixed window strategies |
| `lexigram-web/.../routing/validation.py` | 520 | Request param validation — cohesive middleware |
| `lexigram-workflow/.../bulk/operation.py` | 503 | BulkOperation engine — just barely over, cohesive batch processing |
| `lexigram-multimedia-video/.../processing/argv.py` | 551 | ffmpeg argv builders — pure functions, cohesive command assembly |

## Framework Core (Task 11 — W4 triage)

| File | Lines | Rationale |
|------|-------|-----------|
| `core/lexigram/.../app/base.py` | 621 | Application base class — lifecycle collaborator (`ApplicationLifecycle`) already extracted; residual is the state machine + boot sequence contract that subclasses extend. No second seam without breaking the template-method flow. |
| `core/lexigram/.../di/container/container.py` | 668 | Container facade — already delegates to RegistrarImpl, ResolverImpl, Validator, Diagnostics. Resolution logic is in ServiceResolver. No clean seam for ContainerResolverCore extraction. |
| `core/lexigram/.../domain/models/base.py` | 552 | DomainModel mixin — cohesive auto-dataclass with type hints, Pydantic compat, serialization, validation, field constraints. All tightly coupled; no mixin seam. |
| `core/lexigram/.../primitives/context.py` | 546 | Context management — ContextKey, ContextVarRegistry, Context, RequestContext, factories. Complete self-contained subsystem; splitting creates unnecessary cross-module deps. |

## Contracts Root Facade (Task 9)

| File | Lines | Rationale |
|------|-------|-----------|
| `core/lexigram-contracts/.../contracts/__init__.py` | 619 | **§8-exempt** root facade — exports only; cap does not apply to public-root files per AGENTS.md §8. |

## AI LLM Clients (Task 14 addendum)

| File | Lines | Rationale |
|------|-------|-----------|
| `lexigram-ai-llm/.../clients/anthropic.py` | 518 | Transport adapter for Anthropic Messages API — single-responsibility provider client (same rationale as documented `aws_bedrock.py`). |

## AI Test Residuals (Tasks 5–6 follow-up)

Partial splits were performed; each residual retains cohesive test
families sharing fixtures and mocks.

| File | Lines | Rationale |
|------|-------|-----------|
| `lexigram-ai-rag/tests/unit/test_chunking.py` | 595 | Split performed (`test_chunking_strategies.py` extracted); residual keeps 10 chunker-family test classes (Chunk, FixedSize, Recursive, Semantic, SlidingWindow, Token, Custom, Config, factory, integration) sharing chunk fixtures. |
| `lexigram-ai-rag/tests/unit/test_rag_cache__testragcache.py` | 521 | Split performed (`test_rag_cache.py` extracted); residual covers TestRagCache internals sharing cache fixtures. |
| `lexigram-ai-relay-gateway/tests/unit/test_channels.py` | 558 | Channel resolution tests — per-channel families sharing gateway fixtures. |
| `lexigram-ai-relay-gateway/tests/unit/test_stream.py` | 508 | Stream endpoint tests sharing SSE client fixture; just over limit. |
| `lexigram-ai-relay/tests/unit/relay/test_engine.py` | 539 | Relay engine tests — dispatch/routing/settlement scenarios share engine harness. |

## Admin App (Task 12 — W4 triage)

14 Recipe D files are documented in the package-local register at
`experimental/apps/lexigram-admin/docs/loc_debt.md`. The following 8
admin residents are documented here (not covered there):

| File | Lines | Rationale |
|------|-------|-----------|
| `lexigram-admin/.../dashboard/page_handlers.py` | 544 | Dashboard page handlers — HTMX partial handlers sharing permission checks and settings service. |
| `lexigram-admin/.../realtime/websocket.py` | 536 | WS manager — `ConnectionTracker` already extracted; residual is auth/handshake + message routing inherent to the ASGI socket loop. |
| `lexigram-admin/.../resources/list_renderer.py` | 567 | List renderer — table/pagination/bulk-bar rendering coupled to column spec types. |
| `lexigram-admin/.../services/export/service.py` | 537 | Export service — `ExportJobManager` already extracted; residual coordinates format writers + progress reporting. |
| `lexigram-admin/.../services/filter_manager.py` | 511 | Filter manager — just over limit; query-string parsing + per-field filter application are one concern. |

## CLI & UI Apps

| File | Lines | Rationale |
|------|-------|-----------|
| `lexigram-cli/.../commands/config.py` | 514 | Config command group — get/set/list/validate subcommands sharing config-load bootstrap. |
| `lexigram-cli/.../commands/db.py` | 720 | DB command group — 18 click commands (migrate/seed/backup/restore/shell) sharing `_bootstrap_db_provider`/`_bootstrap_migration_runner`; command modules are flat by convention. |
| `lexigram-cli/.../registry/database.py` | 541 | Database registry checks — provider/driver detection family sharing check scaffolding. |
| `lexigram-cli/.../registry/health.py` | 696 | Health check registry — 12 `HealthCheck` plugin classes (40–60 LOC each) + registry + runner; splitting scatters a plugin set that shares `CheckResult`. |
| `lexigram-cli/.../registry/provider.py` | 611 | Provider registry — package discovery + entry-point scanning for provider packages; cohesive introspection module. |
| `lexigram-ui/.../charts/static.py` | 686 | Static SVG chart renderer — pure render functions; verbosity is SVG markup generation, not logic depth. |
| `lexigram-ui/.../state.py` | 563 | UI state types — signals/stores/value types used together across UI components. |
