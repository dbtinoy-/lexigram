# LOC Debt Register

Files accepted as permanently over the 500-line LOC limit. Each entry
explains why decomposition would not improve maintainability.

## AI Extensions (Task 14 — W4 triage)

| File | Lines | Rationale |
|------|-------|-----------|
| `lexigram-ai-agents/.../executor.py` | 622 | Orchestrator integrating governance, memory, sessions, skills, metrics — already uses `AgentObservability` and `AgentSafetyInfra` composites |
| `lexigram-ai-agents/.../function_calling.py` | 612 | Native tool-calling strategy with retry, guard hooks, and memory context — cohesive strategy with thin private helpers |
| `lexigram-ai-agents/.../plan_execute.py` | 526 | Already delegates to `_executor`, `_planner`, `_types` modules — thin orchestration wrapper |
| `lexigram-ai-governance/.../contributor.py` | 622 | Admin dashboard contributor — widget definitions + renderers tightly coupled to governance billing domain |
| `lexigram-ai-governance/.../tracker.py` | 505 | Budget tracker with sliding-window counters and threshold alerting — self-contained enforcement logic |
| `lexigram-ai-governance/.../persistence.py` | 671 | Three persistence backends (InMemory, Redis, Database) sharing a protocol — each backend is ~100–180 LOC |
| `lexigram-ai-governance/.../pricing.py` | 636 | Expression parser + price engine + `SimpleCostEstimator` — parser internals tightly coupled to evaluation |
| `lexigram-ai-governance/.../reservations.py` | 555 | Admission control across six scope dimensions — atomic reservation logic with sliding windows |
| `lexigram-ai-governance/.../manager.py` | 610 | Governance manager: policy enforcement, budget tracking, audit, resource units — cohesive policy orchestrator |
| `lexigram-ai-llm/.../aws_bedrock.py` | 592 | Transport adapter for Bedrock Converse API — single-responsibility provider client |
| `lexigram-ai-llm/.../pricing/manager.py` | 507 | Pricing manager with builder pattern — cache + source chain + factory methods |
| `lexigram-ai-llm/.../pricing/sources.py` | 538 | Four pricing source implementations sharing common error handling |
| `lexigram-ai-llm/.../registry/core.py` | 583 | Provider registry with 14 built-in providers — registration data is inherently verbose |
| `lexigram-ai-llm/.../security/core.py` | 547 | Prompt injection protection — detection layers + sanitization + rate limiting |
| `lexigram-ai-llm/.../streaming/stream.py` | 511 | Streaming adapters + orchestrator + response aggregation |
| `lexigram-ai-llm/.../typed_responses.py` | 515 | Response type adapters (text, JSON, function call, structured, audio) |
| `lexigram-ai-mcp/.../di/provider.py` | 545 | MCP DI provider — wiring controllers, connectors, handlers, transports, client |
| `lexigram-ai-rag/.../loaders/core.py` | 539 | Document loaders (text, PDF, markdown, HTML, JSON, CSV) — each loader is 40–90 LOC |
| `lexigram-ai-rag/.../pipeline/builder.py` | 605 | RAG pipeline + builder — builder is 390 LOC of configuration wiring |
| `lexigram-ai-relay-gateway/.../passthrough_service.py` | 583 | Passthrough relay — channel selection, billing, upstream transport, settlement |
| `lexigram-ai-workers/.../dlq/worker.py` | 540 | DLQ worker — error classification, retry with backoff, notification, health check |

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
| `core/lexigram/.../di/container/container.py` | 668 | Container facade — already delegates to RegistrarImpl, ResolverImpl, Validator, Diagnostics. Resolution logic is in ServiceResolver. No clean seam for ContainerResolverCore extraction. |
| `core/lexigram/.../domain/models/base.py` | 552 | DomainModel mixin — cohesive auto-dataclass with type hints, Pydantic compat, serialization, validation, field constraints. All tightly coupled; no mixin seam. |
| `core/lexigram/.../primitives/context.py` | 546 | Context management — ContextKey, ContextVarRegistry, Context, RequestContext, factories. Complete self-contained subsystem; splitting creates unnecessary cross-module deps. |
