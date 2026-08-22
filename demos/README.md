# Demos

> 🎯 **Fourteen runnable, fully-gated demo apps** — each one is a living tutorial
> for Lexigram, built on the editable framework packages in this repository:
> nine capability demos plus five auth consoles, all offline-deterministic
> and gated like the framework itself.

---

## 🧭 The demos at a glance

### 🛡️ [resilient-rates](resilient-rates/) — resilience patterns end to end

- 🌐 **REST API** — `GET /rates/{pair}`, `POST /scenario/{name}` live fault flips,
  `GET /stats` counters (`uv run python -m rates serve`, :7073)

An FX rate desk that survives a hostile upstream:

- 💥 **Scriptable faults** — flip `healthy / flaky / down / slow` live via a
  container-managed `FaultController`
- 🔁 **Retry + circuit breaker + timeout** assembled from contract configs
  through a resilience pipeline factory
- ⚡ **Single-flight reads** — per-key locks collapse concurrent misses
- 🧊 **Stale fallback** — upstream failing? Serve the last known-good quote
  while retries exhaust or the circuit is open
- 🎲 **Deterministic** — seeded random-walk quotes make failures reproducible
- 🖥️ **Five-act walkthrough** — `uv run python -m rates demo`

### 📦 [event-driven-orders](event-driven-orders/) — CQRS & event sourcing

- 🌐 **REST API** — `POST /orders`, lifecycle commands, read-model queries,
  outbox inspect/flush (`uv run python -m orders serve`, :7074)

A full order lifecycle driven by messages:

- ✍️ **Commands** — place, pay, ship
- 📢 **Domain events** with handlers and read-side projections
- 🔔 **Notification side effects** — customer-notification handlers subscribed
  on the event bus next to the read-model projection
- 🗳️ **Transactional outbox** — inspect and flush pending publishes
- 🖥️ **CLI-first** — `uv run python -m orders place "Alice" --item "SKU-1,2,9.99"`
  or watch the whole lifecycle via `uv run python -m orders demo`

### 📡 [realtime-monitor](realtime-monitor/) — realtime web console

A live ops dashboard with zero frontend dependencies:

- 🌊 **Server-sent events** — history replay, then live stream with heartbeats
- 🔌 **WebSocket operator channel** wired through the DI provider
- 📊 **Live stats API** powering header chips
- 📨 **Publish from anywhere** — `POST /api/events` accepts events from curl
  or external tools
- 🪶 **Vanilla JS** `EventSource` client — no build step, no npm

### 🧪 [llm-experiment](llm-experiment/) — reproducible AI experiments

LLM evaluation with science-grade determinism:

- 🔒 **Same seed ⇒ same digest** — byte-identical reruns, verified on every run
- 🧬 **Thinking ablation** — measure the cost of reasoning with
  digest-verified delta records
- 🗂️ **Full observability** — tracking, checkpoints, metrics, tracing, and
  post-hoc error analysis persisted per run
- 📓 **Notebook included** — `reproducibility.ipynb` walks the contract

### 📚 [rag-docs](rag-docs/) — RAG over our own docs

- 🌐 **REST API** — `POST /ask {question}` → cited answer,
  `GET /stats` corpus stats (`uv run python -m rag_docs serve`, :7075)

Retrieval-augmented answers from the framework's documentation:

- 🧮 **Deterministic embeddings** — stdlib-only hashing embedder, no model,
  byte-identical answers on re-run
- 🔎 **Pluggable retrieval** — `vector` vs `mmr` strategies through a
  registry, no if/elif dispatch
- 🧊 **In-memory vector store** — chunked markdown upserted at boot
- 🖥️ **Cited answers** — extractive synthesis with `[n] path#chunk`
  citations via `uv run python -m rag_docs demo`

### 🤖 [support-agent](support-agent/) — tool-calling ReAct agent

A support-desk agent driven by a scripted LLM:

- 🧠 **Real agent loop** — THOUGHT/ACTION parsing through the framework's react strategy
- 🔧 **Three container-injected tools** — order lookup, refund policy math, KB search
- 🎬 **Deterministic model boundary** — scripted completions, byte-stable reruns
- 🖥️ **Browser console** — pick a scenario, ask, read the trace table
- 💥 **Failure act included** — unknown tools degrade to failed tool-call records
- 🚀 **Run** — `PYTHONPATH=demos/support-agent/src uv run python -m support_agent`

### 🧠 [memory-chat](memory-chat/) — conversational memory, zero LLM

A concierge that remembers what you tell it:

- 💬 **Facts persist** — stated once, cited turns later via episodic + semantic stores
- 👥 **Two-owner console** — alice's allergies never leak into bob's session
- 🎬 **Demo replay** — scripted two-session transcript proves recall AND isolation
- 🚫 **No model calls** — deterministic template responder keeps runs byte-stable
- 🚀 **Run** — `PYTHONPATH=demos/memory-chat/src uv run python -m memory_chat`

### 🛡️ [ai-guardrails](ai-guardrails/) — guards + budgets, five acts live

One support-request pipeline, unprotected vs protected:

- 🚫 **Injection blocked** · 🕶️ **PII redacted end-to-end** · 📏 **Oversize blocked**
- ⛔ **Restricted model denied** · 💸 **Budget exhausts after three paid turns**
- 🔎 **Live audit trail** — MODEL_DENIED / BUDGET_EXCEEDED rows in the sidebar
- 🎚️ **Protection toggle** — flip guards + governance off and watch the difference
- 🚀 **Run** — `PYTHONPATH=demos/ai-guardrails/src uv run python -m guard_gate`

### ✍️ [prompt-lab](prompt-lab/) — prompt authoring & A/B, zero LLM

Iterate on a support-reply prompt like a scientist:

- 🧬 **Two variants** — terse v1 vs empathetic few-shot v2
- 🕘 **Real versioning** — push revisions, inspect history, roll back live
- 🎯 **Deterministic A/B** — criteria-scored over four seeded cases, byte-stable
- 🖥️ **Lab console** — render previews at any revision side-by-side with scores
- 🚀 **Run** — `PYTHONPATH=demos/prompt-lab/src uv run python -m prompt_lab`

### 🔁 [feedback-loop](feedback-loop/) — ratings become regression suites

Close the quality loop without a model call:

- ⭐ **Rate canned answers** — 1–5 stars captured per trace id
- 📉 **Low ratings promote** — ≤2-rated exchanges become eval samples
- 🎯 **Real harness runs** — QA-scored, tracked under seeded run ids
- 🔎 **Error analysis** — mean/min/max scores and top failing cases printed
- 💻 **CLI-first** — six subcommands; `demo` plays the whole loop

### 🔐 [auth-web](auth-web/) — browser account lifecycle

Register, log in, manage sessions and passwords over `lexigram-auth`:

- 🍪 **Cookie sessions** — `SessionCookieBackend` with revocation across
  browsers, HttpOnly by default
- 🎫 **JWT claims on your profile** — fresh token minted per visit, roles +
  permissions expanded from seeded RBAC definitions
- 🚫 **Lockout built in** — 5 wrong passwords lock the account, constant-time
  verification prevents user enumeration
- 🖥️ **Vanilla JS client** — HTML views + `fetch` against a pure JSON API via
  `uv run python -m auth_web`

### 👥 [auth-rbac](auth-rbac/) — permission matrix console

Role-based access control with live `authorize()` verdicts:

- 👥 **Seeded personas** — viewer / editor / admin logins sharing one password
- 🧾 **Pattern grammar** — `resource.action` permissions with `*` wildcards
  and role inheritance (`editor` ⊃ `viewer`)
- 🧮 **Live matrix** — the grid recomputes via `authorize()` per persona; a
  try-form runs any action/resource pair
- 🛡️ **Guarded resources** — article create denies viewers with 403 + missing
  pattern

### 🔢 [auth-mfa](auth-mfa/) — TOTP challenge console

Two-factor authentication with pending-challenge sessions:

- 📟 **Pending challenge flow** — password issues a pre-auth cookie; only a
  valid TOTP/backup code upgrades it to a real session
- 🗝️ **Enrollment with backup codes** — `enable_totp` returns secret +
  provisioning URI + one-time codes, shown exactly once
- 🚧 **Attempt capping** — 3 wrong codes revoke the challenge back to login
- ⏻ **Disable needs password** — re-verification before TOTP is removed

### 🗝️ [auth-apikeys](auth-apikeys/) — machine authentication

API-key management UI plus an `X-API-Key`-guarded JSON endpoint:

- 🗝️ **Raw key shown once** — hashes persist; the table shows prefixes only
- 🎯 **Scoped keys** — issue with read/write scopes; `/api/me` echoes identity
- 🚫 **Revoke = instant 401** — revoked and garbage keys both rejected
- 🖥️ **Cookie + key side by side** — management needs a session, machines
  need a header

---

## 🚀 Running them

```bash
# ── capability demos ──────────────────────────────────────────────
PYTHONPATH=demos/resilient-rates/src uv run python -m rates serve            # 🛡️ resilience REST API (:7073)
PYTHONPATH=demos/event-driven-orders/src uv run python -m orders demo        # 📦 full CQRS order lifecycle
PYTHONPATH=demos/event-driven-orders/src uv run python -m orders serve       # 📦 same lifecycle as REST API (:7074)
curl -X POST localhost:7073/scenario/down   # …then watch retry/breaker react
PYTHONPATH=demos/support-agent/src uv run python -m support_agent            # 🤖 agent console (:8082)
PYTHONPATH=demos/memory-chat/src uv run python -m memory_chat                # 🧠 memory chat (:8083)
PYTHONPATH=demos/ai-guardrails/src uv run python -m guard_gate               # 🛡️ guardrails playground (:8084)
PYTHONPATH=demos/prompt-lab/src uv run python -m prompt_lab                  # ✍️ prompt lab (:8085)
PYTHONPATH=demos/feedback-loop/src uv run python -m feedback_loop demo       # 🔁 ratings → regression loop
PYTHONPATH=demos/feedback-loop/src uv run python -m feedback_loop serve      # 🔁 same loop as web console (:8086)
PYTHONPATH=demos/rag-docs/src uv run python -m rag_docs demo                 # 📚 cited answers from our own docs
PYTHONPATH=demos/rag-docs/src uv run python -m rag_docs serve                # 📚 same corpus as an ask API (:7075)
PYTHONPATH=demos/realtime-monitor/src uv run python -m ops_console           # 📡 realtime dashboard server (:7071)
uv run python demos/llm-experiment/run_experiment.py                         # 🧪 seeded experiment + rerun

# ── auth consoles ─────────────────────────────────────────────────
PYTHONPATH=demos/auth-web/src uv run python -m auth_web                      # 🔐 account lifecycle (:8081)
PYTHONPATH=demos/auth-rbac/src uv run python -m rbac_console                 # 👥 permission matrix (:8090)
PYTHONPATH=demos/auth-apikeys/src uv run python -m apikey_console            # 🗝️ machine auth keys (:8091)
PYTHONPATH=demos/auth-mfa/src uv run python -m mfa_console                   # 🔢 TOTP challenge (:8092)

make test-demos                                                              # ✅ every demo test suite
```

Each demo boots the real framework — real DI graph, real cache backend,
real resilience pipeline — no mocks where it matters.

---

## ✅ Reviewer gates (same bar as the framework)

- 🎨 **Format + lint** — root `ruff format --check .` / `ruff check .`
  (demo-specific rule relaxations live in the root `pyproject.toml`)
- 🧪 **Tests** — every demo runs its suite in the workspace env
  (`make test-demos`)
- 🔍 **Compile check** — demo sources are compile-gated (`make verify-demos`)
- 🏁 **One command** — `make check-demos` runs tests + compile checks and is
  part of `make ci`; GitHub Actions enforces it in the **Demos gate** job
