# Resilient Rates Demo Spec

> **Date:** 2026-08-21 | **Scope:** `demos/resilient-rates` (new), Makefile, `.github/workflows/ci.yml`, `demos/README.md` | **Status:** Design approved in chat

## Context

The demos are the framework's teaching artifacts, and two shipped subsystems
have zero demo coverage: `lexigram-resilience` (retry, circuit breaker,
pipeline) and `lexigram-cache` (backends, TTL, single-flight locks). A
simulated FX rates service is the natural vehicle: rate fetching is the
canonical resilience use case (flaky upstream, hard outages, stampedes on
recovery), it needs no network, and it fits the existing demo shape
(module + provider + CLI + pytest suite).

Decisions made during brainstorming:

- **Scope:** resilient-rates only (AI analyst demo deferred).
- **Data:** fully simulated provider — deterministic seeded random-walk rates
  plus scriptable fault scenarios; everything runs offline like the other
  demos and the offline CI gate.
- **Interface:** CLI only (argparse subcommands, structlog narration).
- **Approach:** "Scenario console" — contract-first wiring plus a
  FaultController and a scripted `demo` walkthrough that makes retry,
  breaker transitions, stale-serving, and single-flight visible.

## Explicitly rejected

- **Real FX API** (exchangerate.host etc.): network dependency; gated tests
  would need stubbed transport anyway.
- **Browser dashboard** (SSE page à la realtime-monitor): extra surface area;
  CLI narration teaches the patterns better.
- **From-scratch mini breaker/cache**: demos exist to teach framework
  integration, not re-implement it.
- **forex-trading-journal**: same shape as event-driven-orders, no new
  subsystem coverage.

## Architecture

```
demos/resilient-rates/
├── src/rates/
│   ├── domain.py       # RateQuote frozen dataclass: pair, rate, ts, source
│   ├── provider.py     # SimulatedRatesProvider + FaultController
│   ├── service.py      # RatesService: cache-aside read path + stats
│   ├── module.py       # RatesModule(imports=[ResilienceModule, CacheModule])
│   ├── di/provider.py  # RatesProvider: pipeline built once at boot
│   └── main.py         # CLI: fetch · scenario · stats · stampede · demo
├── tests/              # boots the real module graph
└── README.md           # + conftest.py putting src on sys.path
```

### Components

| Component | Responsibility | Dependencies (constructor-injected) |
|---|---|---|
| `RateQuote` | Frozen value: pair, rate, fetched-at ts, source (`upstream`\|`cache`\|`stale`) | none |
| `SimulatedRatesProvider` | Seeded random-walk quotes per pair; raises `UpstreamTimeoutError`/`UpstreamUnavailableError` per active scenario | none (seeded RNG) |
| `FaultController` | Singleton holding active scenario ∈ `healthy\|flaky\|down\|slow`; explicit state changes only | none |
| `RatesService` | Cache-aside read path; stale fallback while breaker open; stats counters (hits, misses, upstream_calls, retries, staleness served) | `CacheBackendProtocol`, `ResiliencePipelineFactoryProtocol`, `SimulatedRatesProvider`, `FaultController` |
| `RatesProvider` | Builds one resilience pipeline at boot — retry (3 attempts, exponential backoff) → circuit breaker (threshold 3, open window 0.2s) → timeout; registers services as singletons | container protocols |
| `RatesModule` | `imports=[ResilienceModule.configure(), CacheModule.configure(memory)]`; exports consumer-facing contracts | framework |

No `Any` on injected parameters; all resolution through the container;
absolute imports; Google docstrings on public members.

### Read path

1. `fetch(pair)` → cache `get(key=pair)`; hit ⇒ return quote (`source=cache`).
2. Miss ⇒ `pipeline.execute(provider.fetch(pair))`.
3. Success ⇒ cache `set(ttl=60s)`, return (`source=upstream`); counters updated.
4. `CircuitOpenError` (or breaker already open) ⇒ serve last-known quote from
   an in-service stale store (`source=stale`) or raise `RateUnavailableError`
   if none exists. Stale logic lives in the service — only it owns cache
   state; the pipeline stays pure retry/breaker/timeout.

### The `demo` walkthrough

One command, five acts, deterministic end to end:

1. **healthy** — miss → upstream OK → cached; second fetch → hit.
2. **flaky** — 70% timeouts → retry logs visible → succeeds on attempt k.
3. **down** — hard failures ×3 → `breaker_opened` → subsequent fetches serve
   `stale`.
4. **heal** — scenario back to healthy → open window passes → HALF_OPEN probe
   succeeds → CLOSED.
5. **stampede** — cache cleared, 10 concurrent fetches → single-flight lock →
   exactly 1 upstream call.

Structlog events narrate each decision: `cache_hit`, `retry_scheduled`,
`breaker_opened`, `breaker_half_open`, `breaker_closed`,
`single_flight_wait`, `stale_served`. `stats` prints the counter table;
`scenario <name>` flips the FaultController between acts when driving manually.

## Error handling

- Demo-local hierarchy over contracts bases: `RateProviderError(InfrastructureError)`
  → `UpstreamTimeoutError`, `UpstreamUnavailableError` (raised by the
  simulated provider — the infra failures the pipeline absorbs),
  `RateUnavailableError` (no quote obtainable and no stale copy).
- `CircuitOpenError` is imported from `lexigram-resilience`; only the service
  catches it (fallback path). All other exceptions propagate.
- Cache contract methods return `Result[...]` — checked via `is_ok()` before
  any unwrap; no blind unwraps anywhere.
- No new exception types in contracts; nothing to regenerate in error-code docs.

## Testing

Offline and deterministic; suite boots the real module graph via
`Application.boot(name="rates-test", modules=[RatesModule.configure()])`.

Determinism levers: seeded provider RNG (identical quotes every run);
breaker open window 0.2s so tests may use short real sleeps (no clock fakes);
FaultController set directly in tests rather than via sleeps.

Required cases:

1. Cache miss → upstream call → cached; second fetch is a hit (upstream_calls == 1).
2. Under flaky scenario, retry recovers (seeded attempt sequence asserted).
3. Breaker opens after 3 consecutive failures; opens without calling upstream again.
4. While OPEN, fetch serves `source=stale`; no upstream call attempted.
5. After heal + open window, HALF_OPEN probe closes the circuit.
6. Stampede: 10 concurrent misses → exactly 1 upstream call (single-flight).
7. CLI smoke: `demo` runs all five acts; output contains the key narrations (capsys).

Every task ships its tests in the same commit; `make check-demos` green at the end.

## Repo gates

- `Makefile`: add `demos/resilient-rates/tests` to `DEMO_TEST_DIRS` and the
  demo dir to `DEMO_COMPILE_DIRS`; refresh the `test-demos` help line.
- `.github/workflows/ci.yml`: add the test path to the Demos-gate pytest
  command **in the same change** (the round-2 staleness lesson).
- `demos/README.md`: list the fourth demo alongside the other three.
- Ruff check/format scoped to the new tree; compile gate covers it via
  `make verify-demos`.

## Requirements

1. R1: New demo package follows the established layout; boots through the
   container with ResilienceModule and CacheModule imported — no manual
   instantiation of services.
2. R2: Simulated provider is seeded and scenario-driven; scenarios are
   healthy/flaky/down/slow, switchable by CLI and tests.
3. R3: Read path implements cache-aside with TTL 60s, stale fallback while
   the breaker is open, and stats counters exposed via `stats`.
4. R4: Resilience pipeline (retry → circuit → timeout) is built through
   `ResiliencePipelineFactoryProtocol` from the framework, not hand-rolled.
5. R5: Stampede protection demonstrably yields 1 upstream call under N
   concurrent misses.
6. R6: `demo` subcommand walks all five acts deterministically with structlog
   narration.
7. R7: Full test suite per the Testing section passes offline; gates wired in
   the same change set; `make check-demos` green.

## Global constraints

- Python 3.11+, uv workspace, absolute imports only
- Commit convention: `<emoji> <type>(<scope>): <summary>`; no worktrees, no
  branches, no Co-authored-by trailers
- Demo ruff exemptions (T201 prints, ANN) remain legal — CLI prints are fine
- Shared working tree: `git status --short` before commits; pathspec staging
- Demos excluded from aggregate pytest run; run via `make test-demos` or
  explicit paths
