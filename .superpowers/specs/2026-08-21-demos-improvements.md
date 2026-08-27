# Demos Improvement Spec

> **Date:** 2026-08-21 | **Scope:** `demos/` (all three demos) | **Status:** Approved direction

## Context

The three demos are the framework's teaching artifacts. Reviewers copy their
patterns, so anything the demos do "wrong" propagates. An audit found five
concrete gaps: one gate hole, two rule violations, one reliability bug, and
one typing debt cluster.

## Problems

### P1 — llm-experiment has no test gate (highest value)

`demos/llm-experiment` is compile-checked only (`make verify-demos`). The
other two demos run pytest suites in `make test-demos`. The harness is fully
offline and deterministic (same seed + config ⇒ identical digest), so it is
trivially testable — the missing suite is pure gate debt.

- `run_experiment(config: dict, *, seed: int, out_dir: Path, ablate: str | None = None) -> ExperimentResult`
  (`demos/llm-experiment/harness.py:247`)
- `ExperimentResult` is frozen with `.digest`, `.run_id`, `.metrics`, `.result`
- `metrics_delta(run_a, run_b) -> dict[str, Any]` (`harness.py:519`)
- Config shape is `{"experiment": {...}}` mirroring `experiment.yaml`
- Artifacts land under `out_dir/runs/<run_id>/` — tests must use `tmp_path`

### P2 — event-driven-orders manually instantiates OrdersApi

`main.py:66-72` resolves five services then constructs `OrdersApi(...)` by
hand. AGENTS.md §4.3: *"Never instantiate services directly — always resolve
through the container."* The facade must be container-managed like every other
service.

Constraint: registration must happen in `register()` (container freezes before
`boot()`), but `OrdersApi`'s command-bus dependency is only fully wired during
`boot()`. Precedent: `CacheProvider` registers lazy factories in `register()`
(`factory=lambda: self.get_backend(None)`) that read state populated by
`boot()`. Same pattern applies here.

### P3 — event-driven-orders duplicates handler plumbing

`PlaceOrderHandler`, `PayOrderHandler`, `ShipOrderHandler` each repeat an
identical constructor (repository/event_bus/outbox) and an identical
stage → publish → warn-log block (~60 duplicated lines). AGENTS.md §4.3:
*"Duplicate or redundant code — extract, don't copy."* Template-base naming
per §5.8: `*Base` suffix.

### P4 — realtime-monitor heartbeat task dies silently

`di/provider.py:70` creates the heartbeat task but stores no supervision: if
`publish()` ever raises, the task dies and dashboards silently stop seeing
traffic until restart. Required: done-callback that logs unexpected death and
restarts the loop (cancelled/shutdown exits excluded). RUF006-compliant task
storage already exists; shutdown cancellation stays as-is.

### P5 — realtime-monitor request parameters untyped

`EventsStreamHandler.stream(self, request)` and all four controller methods
use bare `request=None`. Demos are ANN-exempt in ruff, but they teach
patterns. The framework's own `AbstractSSEHandler` annotates
`starlette.requests.Request` (`packages/lexigram-web/src/lexigram/web/sse/handler.py:13,74`)
— demos should match. Defaults (`= None`) must be preserved exactly; only
annotations change, so route binding behavior is untouched.

### Explicitly rejected

- **Background outbox dispatcher** (event-driven-orders): the manual
  `outbox` CLI command is the demo's teaching intent (inspect staged records,
  then flush). A background loop would hide the pattern the demo exists to
  show.
- **StaticFiles mount** for realtime-monitor assets: zero-dependency goal is
  documented in the demo README; two routes are deliberate.

## Requirements

1. R1: `make test-demos` runs an llm-experiment pytest suite covering digest
   determinism (same seed ⇒ same digest), seed sensitivity (different seed ⇒
   different digest), and ablation delta behavior.
2. R2: `OrdersApi` resolves from the container; `main.py` performs exactly one
   resolve; module exports list `OrdersApi`.
3. R3: One shared base class owns handler construction and event publishing;
   behavior of all three handlers is unchanged (existing suite passes).
4. R4: Heartbeat task crash is logged via structlog and the loop restarts;
   shutdown still cancels cleanly.
5. R5: All request parameters in `console.py` annotated `Request` /
   `Request | None`; no default values changed.
6. R6: `order_event()`'s `aggregate_id` parameter typed `UUID | None`.
7. R7: Every task ships its tests in the same commit; full gate
   (`make check-demos`) green at the end.

## Global constraints

- Python 3.11+, uv workspace, absolute imports only
- Google-style docstrings on new public members
- Commit convention: `<emoji> <type>(<scope>): <summary>` (e.g.
  `✅ test(demos): ...`, `♻️ refactor(demos): ...`)
- No worktrees, no branches, no Co-authored-by trailers
- Demo ruff exemptions (`T201`, `INP001`, `ANN`) remain in force — do not
  rely on them for new strict-code, but print-based CLIs stay legal
