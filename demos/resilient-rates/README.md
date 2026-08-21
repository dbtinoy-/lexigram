# Resilient Rates Demo

Demonstrates the **resilience + cache subsystems** of Lexigram.

This demo is a small FX rate desk in front of a hostile upstream. Every read
flows through a **cache-aside** lookup (60s TTL) and a **resilience pipeline**
assembled from contract configs — retry with backoff, a circuit breaker, and a
timeout. When the breaker is open, the service falls back to the last
known-good **stale** quote; when the cache is cold, per-key **single-flight**
locks collapse concurrent misses into one upstream call.

No network, broker, or external service is required — the upstream is a
deterministic seeded random-walk provider whose faults you script live.

## What it shows

| Piece | Where | Lexigram API used |
|-------|-------|-------------------|
| Resilience pipeline (retry → breaker → timeout) | `src/rates/service.py` | `ResiliencePipelineFactoryProtocol`, `RetryConfig`, `CircuitBreakerConfig`, `TimeoutConfig` |
| Cache-aside reads + TTL writes | `src/rates/service.py` | `CacheBackendProtocol`, `Result[Ok, Err]` cache results |
| Stale fallback while the circuit is OPEN | `src/rates/service.py` | `CircuitOpenError`, `RetryExhaustedError` handling |
| Single-flight (per-key locks) | `src/rates/service.py` | `asyncio.Lock` keyed map around the pipeline call |
| Scriptable fault scenarios | `src/rates/provider.py` | `FaultController` (container-managed), `Scenario` enum |
| Module wiring | `src/rates/module.py` | `ResilienceModule.configure()`, `CacheModule.configure()`, `@module` |
| DI provider | `src/rates/di/provider.py` | `Provider` registering service + faults |
| CLI | `src/rates/main.py` | `Application.boot()` + container resolution |

## Scenarios

Flip upstream health at any time with `uv run python -m rates scenario <name>`:

| Scenario | Upstream behavior |
|----------|-------------------|
| `healthy` | Always answers with a fresh random-walk quote |
| `flaky` | ~70% of calls raise a timeout — retries absorb them |
| `down` | Hard failure on every call — breaker opens, stale serves |
| `slow` | Adds latency to every call — exercises the timeout tier |

## Run it

```bash
uv run python -m rates demo
```

`demo` runs the whole story in one process across five acts:

1. **healthy — cache-aside**: first fetch misses and hits the upstream, second
   fetch is served from cache.
2. **flaky — retries absorb timeouts**: backoff retries soak up the flaky
   upstream until a quote lands.
3. **down — breaker opens, stale serves reads**: after the threshold the
   circuit opens and every read falls back to the last known-good quote.
4. **heal — HALF_OPEN probe closes the circuit**: recovery window passes, one
   probe succeeds, the circuit closes.
5. **stampede — single-flight collapses 10 into 1**: ten concurrent fetchers
   of a cold key produce exactly one upstream call.

You can also drive each piece yourself:

```bash
uv run python -m rates fetch EUR/USD        # one quote (cache → upstream → stale)
uv run python -m rates scenario flaky       # flip upstream health live
uv run python -m rates stats                # hits / misses / upstream / retries / stale
uv run python -m rates clear-cache          # drop cached quotes
uv run python -m rates stampede USD/JPY     # 10 concurrent fetches of one pair
```

All state is in-memory and per-process: each invocation boots a fresh
application, so scenarios and caches reset between commands. Use `demo` for
the full narrative in a single process, or the test suite below.

## Layout

```
demos/resilient-rates/
├── src/rates/
│   ├── domain.py          # RateQuote value type
│   ├── exceptions.py      # UpstreamTimeoutError / UpstreamUnavailableError / RateUnavailableError
│   ├── provider.py        # SimulatedRatesProvider (seeded random walk) + FaultController + Scenario
│   ├── service.py         # RatesService: cache-aside + resilience pipeline + single-flight + stale tier
│   ├── di/provider.py     # RatesProvider (wires cache, pipeline factory, provider, faults)
│   ├── module.py          # RatesModule (imports ResilienceModule + CacheModule)
│   └── main.py            # CLI + five-act demo
└── tests/                 # pytest suite (boots the module, drives every scenario)
```

## Tests

```bash
uv run pytest demos/resilient-rates/tests -q
```

The tests boot the real module (framework memory cache backend + real
resilience pipeline), script each fault scenario through the
`FaultController`, and assert on stats: retry absorption, breaker opening,
stale serving, HALF_OPEN healing, and single-flight collapse.
