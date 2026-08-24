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
