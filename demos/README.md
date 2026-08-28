# Demos

> **Twenty-two runnable, fully-gated demo apps** — each one is a living tutorial
> for Lexigram, built on the editable framework packages in this repository:
> a hub console plus focused capability and infrastructure demos, all
> web-first and deterministic where the domain allows it.

---

## The demos at a glance

### [demo-hub](demo-hub/) — one port for the whole fleet

- **Hub console** — `http://127.0.0.1:7000` lists every demo with live
  status (`PYTHONPATH=demos/demo-hub/src uv run python -m demo_hub`, :7000)

The launchpad for visitors:

- **Single process** — the hub boots each demo's real `Application`
  in-process and mounts it under `/demos/<slug>/`; no other ports needed
- **Live health** — `/api/status` reports every embedded demo; cards turn
  green as each child finishes booting
- **Standalone preserved** — every demo still runs alone on its own port
  exactly as documented below

### [resilient-rates](resilient-rates/) — resilience patterns end to end

- **REST API** — `GET /rates/{pair}`, `POST /scenario/{name}` live fault flips,
  `GET /stats` counters (`uv run python -m rates serve`, :7073)

An FX rate desk that survives a hostile upstream:

- **Scriptable faults** — flip `healthy / flaky / down / slow` live via a
  container-managed `FaultController`
- **Retry + circuit breaker + timeout** assembled from contract configs
  through a resilience pipeline factory
- **Single-flight reads** — per-key locks collapse concurrent misses
- **Stale fallback** — upstream failing? Serve the last known-good quote
  while retries exhaust or the circuit is open
- **Deterministic** — seeded random-walk quotes make failures reproducible
- **Five-act walkthrough** — the browser's **Run 5-Act Demo** control drives
  all resilience acts with live feedback

### [event-driven-orders](event-driven-orders/) — CQRS & event sourcing

- **REST API** — `POST /orders`, lifecycle commands, read-model queries,
  outbox inspect/flush (`uv run python -m orders serve`, :7074)

A full order lifecycle driven by messages:

- **Commands** — place, pay, ship
- **Domain events** with handlers and read-side projections
- **Notification side effects** — customer-notification handlers subscribed
  on the event bus next to the read-model projection
- **Transactional outbox** — inspect and flush pending publishes
- **Browser-first lifecycle** — place, pay, ship, flush the outbox, or run
  the complete lifecycle from the order console

### [realtime-monitor](realtime-monitor/) — realtime web console

A live ops dashboard with zero frontend dependencies:

- **Server-sent events** — history replay, then live stream with heartbeats
- **WebSocket operator channel** wired through the DI provider
- **Live stats API** powering header chips
- **Publish from anywhere** — `POST /api/events` accepts events from curl
  or external tools
- **Vanilla JS** `EventSource` client — no build step, no npm

### [rag-docs](rag-docs/) — RAG over our own docs

- **REST API** — `POST /ask {question}` → cited answer,
  `GET /stats` corpus stats (`uv run python -m rag_docs serve`, :7075)

Retrieval-augmented answers from the framework's documentation:

- **Deterministic embeddings** — stdlib-only hashing embedder, no model,
  byte-identical answers on re-run
- **Pluggable retrieval** — `vector` vs `mmr` strategies through a
  registry, no if/elif dispatch
- **In-memory vector store** — chunked markdown upserted at boot
- **Cited answers** — extractive synthesis with `[n] path#chunk`
  citations, plus a browser-guided three-question demo

### [support-agent](support-agent/) — tool-calling ReAct agent

A support-desk agent driven by a scripted LLM:

- **Real agent loop** — THOUGHT/ACTION parsing through the framework's react strategy
- **Three container-injected tools** — order lookup, refund policy math, KB search
- **Deterministic model boundary** — scripted completions, byte-stable reruns
- **Browser console** — pick a scenario, ask, read the trace table
- **Failure act included** — unknown tools degrade to failed tool-call records
- **Run** — `PYTHONPATH=demos/support-agent/src uv run python -m support_agent`

### [memory-chat](memory-chat/) — conversational memory, zero LLM

A concierge that remembers what you tell it:

- **Facts persist** — stated once, cited turns later via episodic + semantic stores
- **Two-owner console** — alice's allergies never leak into bob's session
- **Demo replay** — scripted two-session transcript proves recall AND isolation
- **No model calls** — deterministic template responder keeps runs byte-stable
- **Run** — `PYTHONPATH=demos/memory-chat/src uv run python -m memory_chat`

### [ai-guardrails](ai-guardrails/) — guards + budgets, five acts live

One support-request pipeline, unprotected vs protected:

- **Injection blocked** · **PII redacted end-to-end** · **Oversize blocked**
- **Restricted model denied** · **Budget exhausts after three paid turns**
- **Live audit trail** — MODEL_DENIED / BUDGET_EXCEEDED rows in the sidebar
- **Protection toggle** — flip guards + governance off and watch the difference
- **Run** — `PYTHONPATH=demos/ai-guardrails/src uv run python -m guard_gate`

### [prompt-lab](prompt-lab/) — prompt authoring & A/B, zero LLM

Iterate on a support-reply prompt like a scientist:

- **Two variants** — terse v1 vs empathetic few-shot v2
- **Real versioning** — push revisions, inspect history, roll back live
- **Deterministic A/B** — criteria-scored over four seeded cases, byte-stable
- **Lab console** — render previews at any revision side-by-side with scores
- **Run** — `PYTHONPATH=demos/prompt-lab/src uv run python -m prompt_lab`

### [feedback-loop](feedback-loop/) — ratings become regression suites

Close the quality loop without a model call:

- **Rate canned answers** — 1–5 stars captured per trace id
- **Low ratings promote** — ≤2-rated exchanges become eval samples
- **Real harness runs** — QA-scored, tracked under seeded run ids
- **Error analysis** — mean/min/max scores and top failing cases printed
- **Web console** — ask, rate, inspect stats, and run regressions directly
  from the browser (`python -m feedback_loop` boots :8086)

### [auth-web](auth-web/) — browser account lifecycle

Register, log in, manage sessions and passwords over `lexigram-auth`:

- **Cookie sessions** — `SessionCookieBackend` with revocation across
  browsers, HttpOnly by default
- **JWT claims on your profile** — fresh token minted per visit, roles +
  permissions expanded from seeded RBAC definitions
- **Lockout built in** — 5 wrong passwords lock the account, constant-time
  verification prevents user enumeration
- **Vanilla JS client** — HTML views + `fetch` against a pure JSON API via
  `uv run python -m auth_web`

### [auth-rbac](auth-rbac/) — permission matrix console

Role-based access control with live `authorize()` verdicts:

- **Seeded personas** — viewer / editor / admin logins sharing one password
- **Pattern grammar** — `resource.action` permissions with `*` wildcards
  and role inheritance (`editor` ⊃ `viewer`)
- **Live matrix** — the grid recomputes via `authorize()` per persona; a
  try-form runs any action/resource pair
- **Guarded resources** — article create denies viewers with 403 + missing
  pattern

### [auth-mfa](auth-mfa/) — TOTP challenge console

Two-factor authentication with pending-challenge sessions:

- **Pending challenge flow** — password issues a pre-auth cookie; only a
  valid TOTP/backup code upgrades it to a real session
- **Enrollment with backup codes** — `enable_totp` returns secret +
  provisioning URI + one-time codes, shown exactly once
- **Attempt capping** — 3 wrong codes revoke the challenge back to login
- **Disable needs password** — re-verification before TOTP is removed

### [auth-apikeys](auth-apikeys/) — machine authentication

API-key management UI plus an `X-API-Key`-guarded JSON endpoint:

- **Raw key shown once** — hashes persist; the table shows prefixes only
- **Scoped keys** — issue with read/write scopes; `/api/me` echoes identity
- **Revoke = instant 401** — revoked and garbage keys both rejected
- **Cookie + key side by side** — management needs a session, machines
  need a header

### [llm-router](llm-router/) — deterministic LLM client patterns

Content generation and structured extraction without an API key:

- **Scripted client** — deterministic responses for repeatable tests
- **Content generation** — style control and retry handling
- **Structured extraction** — parse model output into typed product data

### [monitor-stack](monitor-stack/) — the Lexigram MonitorModule

A browser console over the package's real observability protocols:

- **Health registry** — register and run a readiness check
- **Metrics** — counters, gauges, histograms, and instrument introspection
- **Tracing** — timed spans with IDs and attributes through DI

### [queue-worker](queue-worker/) — an automatic Lexigram consumer

Publish to one `tasks` topic and watch the package consumer handle messages:

- **QueueProtocol** — `QueueModule.stub()` owns the backend and lifecycle
- **MessageConsumer** — subscription starts at provider boot; no pull CLI
- **Retry metadata** — `BusMessage` receives the configured retry policy

### [rag-pipeline](rag-pipeline/) — Lexigram VectorModule retrieval

A complete retrieval pipeline without an external vector database:

- **VectorStoreProtocol** — create a dimensioned cosine collection at boot
- **Chunking** — split documents into indexable pieces
- **Context synthesis** — format ranked sources for generation

### [sql-repository](sql-repository/) — Lexigram DatabaseModule CRUD

A single task resource backed by an in-memory SQLite database:

- **DatabaseProviderProtocol** — schema, parameterized queries, and health
- **Repository boundary** — SQL stays out of the thin HTTP controller
- **Browser mutations** — create, update, delete, and aggregate stats

### [webhook-relay](webhook-relay/) — Lexigram WebhookModule verification

A browser-visible inbound webhook flow without an external receiver:

- **Subscriptions** — package-managed URL validation and secret generation
- **HMAC-SHA256** — verify canonical raw payloads in constant time
- **Accepted ledger** — keep the demo focused while making results visible

### [feature-flags](feature-flags/) — Lexigram FeatureFlagsModule

A release desk for controlled rollouts:

- **Evaluation context** — deterministic percentage, variant, and user-attribute decisions
- **Runtime controls** — force a flag on/off, clear overrides, and flush TTL cache
- **Audit trail** — inspect the package-owned FlagManager override history

### [approval-flow](approval-flow/) — Lexigram WorkflowModule

An interactive purchase approval state machine:

- **Approval gates** — manager and finance decisions through real StateMachine transitions
- **ApprovalChain preview** — run an ALL policy without mutating the request
- **Retry and compensation** — recover rejected or approved flows and inspect transition history

### [artifact-vault](artifact-vault/) — Lexigram StorageModule

A browser object-storage workbench using the memory driver:

- **Upload and metadata** — content types, owner metadata, size, and ETag
- **Preview and delete** — exercise list, info, download, and delete operations
- **Honest access capabilities** — see public URL behavior and why memory has no presigned URL

---

## Running them

```bash
# ── hub: one port serves every demo ───────────────────────────────
(cd demos/demo-hub && PYTHONPATH=src uv run python -m demo_hub)                 # fleet console (:7000)

# ── standalone mode: any demo on its own port ─────────────────────
# The hub is the recommended first glance; these commands are for local
# development when one console needs to run by itself.
PYTHONPATH=demos/resilient-rates/src uv run python -m rates                 # rate desk (:7073)
PYTHONPATH=demos/event-driven-orders/src uv run python -m orders            # order console (:7074)
PYTHONPATH=demos/support-agent/src uv run python -m support_agent           # agent console (:8082)
PYTHONPATH=demos/memory-chat/src uv run python -m memory_chat               # memory chat (:8083)
PYTHONPATH=demos/ai-guardrails/src uv run python -m guard_gate              # guardrails playground (:8084)
PYTHONPATH=demos/prompt-lab/src uv run python -m prompt_lab                # prompt lab (:8085)
PYTHONPATH=demos/feedback-loop/src uv run python -m feedback_loop           # feedback loop (:8086)
PYTHONPATH=demos/rag-docs/src uv run python -m rag_docs                    # RAG docs console (:7075)
PYTHONPATH=demos/realtime-monitor/src uv run python -m ops_console          # realtime dashboard (:7071)

# ── auth consoles ─────────────────────────────────────────────────
PYTHONPATH=demos/auth-web/src uv run python -m auth_web                      # account lifecycle (:8081)
PYTHONPATH=demos/auth-rbac/src uv run python -m rbac_console                 # permission matrix (:8090)
PYTHONPATH=demos/auth-apikeys/src uv run python -m apikey_console            # machine auth keys (:8091)
PYTHONPATH=demos/auth-mfa/src uv run python -m mfa_console                   # TOTP challenge (:8092)
PYTHONPATH=demos/llm-router/src uv run python -m content_gen                # LLM client patterns (:8093)
PYTHONPATH=demos/monitor-stack/src uv run python -m monitorstack             # observability (:8094)
PYTHONPATH=demos/queue-worker/src uv run python -m queueworker              # queue worker (:8095)
PYTHONPATH=demos/rag-pipeline/src uv run python -m ragdocs                  # RAG pipeline (:8096)
PYTHONPATH=demos/sql-repository/src uv run python -m taskapp               # SQL repository (:8097)
PYTHONPATH=demos/webhook-relay/src uv run python -m webhookrelay           # webhook relay (:8098)
PYTHONPATH=demos/feature-flags/src uv run python -m release_control     # release control (:8099)
PYTHONPATH=demos/approval-flow/src uv run python -m approval_flow         # approval flow (:8100)
PYTHONPATH=demos/artifact-vault/src uv run python -m artifact_vault       # artifact vault (:8101)

make test-demos                                                              # every demo test suite
```

Each demo boots the real framework — real DI graph, real cache backend,
real resilience pipeline — no mocks where it matters.

---

## Demo architecture (the Blueprint)

Every demo is built from one shape so the fleet reads like a single codebase:

- **`application.yaml`** carries every runtime knob — server host/port and
  security toggles under `web:`, demo-specific knobs (scenarios, seeds,
  quotas) under `demo:`. Python contains zero literal configuration;
  services receive a frozen `DemoConfig` through DI.
- **`src/<pkg>/module.py`** composes framework modules (`WebModule`,
  `ResilienceModule`, …) and registers one provider; **providers** wire
  singletons and expose `health_check`; **controllers** are stateless HTTP
  adapters; **services** own domain logic behind contracts and return
  `Result[T, E]`.
- **Errors** speak RFC-9457 `ProblemDetail`; **logging** is structured
  (`get_logger`) — walkthroughs narrate with events, never `print`.
- **Time, identity, hashing** come from the framework's ambient capabilities
  (seeded randomness stays stdlib on purpose — determinism is the feature).
- **Tests** fake only at contract boundaries; every public route has an ASGI
  round-trip test.

---

## Reviewer gates (same bar as the framework)

- **Format + lint** — root `ruff format --check .` / `ruff check .`
  (demo-specific rule relaxations live in the root `pyproject.toml`)
- **Tests** — every demo runs its suite in the workspace env
  (`make test-demos`)
- **Compile check** — demo sources are compile-gated (`make verify-demos`)
- **One command** — `make check-demos` runs tests + compile checks and is
  part of `make ci`; GitHub Actions enforces it in the **Demos gate** job
