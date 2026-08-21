# Demos

> 🎯 **Four runnable, fully-gated demo apps** — each one is a living tutorial
> for a Lexigram superpower, built on the editable framework packages in this
> repository.

---

## 🧭 The demos at a glance

### 🛡️ [resilient-rates](resilient-rates/) — resilience patterns end to end

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

A full order lifecycle driven by messages:

- ✍️ **Commands** — place, pay, ship
- 📢 **Domain events** with handlers and read-side projections
- 🗳️ **Transactional outbox** — inspect and flush pending publishes
- 🖥️ **CLI-first** — `uv run python -m orders place "Alice" --item "SKU-1,2,9.99"`

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

---

## 🚀 Running them

```bash
uv run python -m orders demo         # 📦 full order lifecycle in one process
uv run python -m ops_console         # 📡 boot the realtime dashboard server
python demos/llm-experiment/run_experiment.py   # 🧪 seeded experiment + rerun
make test-demos                      # ✅ every demo test suite
```

Each demo boots the real framework — real DI graph, real cache backend,
real resilience pipeline — no mocks where it matters.

---

## ✅ Reviewer gates (same bar as the framework)

- 🎨 **Format + lint** — root `ruff format --check .` / `ruff check .`
  (demo-specific rule relaxations live in the root `pyproject.toml`)
- 🧪 **Tests** — all four demos run their suites in the workspace env
  (`make test-demos`)
- 🔍 **Compile check** — demo sources are compile-gated (`make verify-demos`)
- 🏁 **One command** — `make check-demos` runs tests + compile checks and is
  part of `make ci`; GitHub Actions enforces it in the **Demos gate** job
