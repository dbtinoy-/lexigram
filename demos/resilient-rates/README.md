# Resilient Rates Demo

> Module name: `rates` — run with `PYTHONPATH=src uv run python -m rates`

Demonstrates the **resilience + cache subsystems** of Lexigram.

This demo is a small FX rate desk in front of a hostile upstream. Every read
flows through a **cache-aside** lookup (60s TTL) and a **resilience pipeline**
assembled from contract configs — retry with backoff, a circuit breaker, and a
timeout. When the breaker is open, the service falls back to the last
known-good **stale** quote; when the cache is cold, per-key **single-flight**
locks collapse concurrent misses into one upstream call.

No network, broker, or external service is required — the upstream is a
deterministic seeded random-walk provider whose faults you script live.

## Lexigram concepts used

| Concept | Where in this demo | Your app |
|---------|-------------------|----------|
| Composition root | `app.py` | Replace modules/providers list |
| Resilience pipeline | `services/rates_service.py` | `ResiliencePipelineFactoryProtocol` |
| Cache-aside + stale | `services/rates_service.py` | `CacheBackendProtocol`, `StampedeProtectedCache` |
| Scriptable faults | `repository/simulated_upstream.py` | `FaultController` via DI |
| Custom config model | `config.py` → `RatesConfig` | Add demo-specific knobs in `demo:` section |
| Provider lifecycle | `di/provider.py` | register() binds, boot() wires faults |

## What it shows

| Piece | Where | Lexigram API used |
|-------|-------|-------------------|
| Resilience pipeline (retry → breaker → timeout) | `services/rates_service.py` | `ResiliencePipelineFactoryProtocol`, `RetryConfig`, `CircuitBreakerConfig`, `TimeoutConfig` |
| Cache-aside reads + TTL writes | `services/rates_service.py` | `CacheBackendProtocol`, `Result[Ok, Err]` cache results |
| Stale fallback while the circuit is OPEN | `services/rates_service.py` | `CircuitOpenError`, `RetryExhaustedError` handling |
| Single-flight (per-key locks) | `services/rates_service.py` | `StampedeProtectedCache` around the pipeline call |
| Scriptable fault scenarios | `repository/simulated_upstream.py` | `FaultController` (container-managed), `Scenario` enum |
| Module wiring | `app.py` | `ResilienceModule.configure()`, `CacheModule.configure()`, `WebModule.configure()` |
| DI provider | `di/provider.py` | `Provider` registering service + faults |
| REST API | `controllers/api.py` | `Controller`, `@get`, `@post`, `ResultResponseMapper` |
| Web UI | `ui/views/desk.html` + `ui/static/app.js` | Vanilla JS client for all endpoints |

## Run it

```bash
cd demos/resilient-rates
PYTHONPATH=src uv run python -m rates              # start the web console
```

Open `http://localhost:7073` for the rate desk console. Use **Run 5-Act
Demo** for the guided resilience walkthrough, or operate each scenario,
cache, quote, and stampede control directly from the page. Every control
shows its in-progress state and reports success or failure in the activity log.

## Layout — read it in this order

| # | File | Lesson |
|---|------|--------|
| 1 | `src/rates/app.py` | ⭐ Composition root: modules → providers → create_app |
| 2 | `src/rates/main.py` | Lifecycle: `Application.start/stop`, graceful shutdown |
| 3 | `src/rates/config.py` | Custom config model: `RatesConfig` for `demo:` section |
| 4 | `src/rates/di/provider.py` | DI wiring: register() binds pipeline + cache, boot() wires faults |
| 5 | `src/rates/services/rates_service.py` | Cache-aside + resilience + single-flight + stale |
| 6 | `src/rates/repository/simulated_upstream.py` | FaultController: scriptable upstream scenarios |
| 7 | `src/rates/controllers/api.py` | REST API: fetch, stats, scenario, cache, stampede, demo |
| 8 | `application.yaml` | Cache + resilience + web + demo config sections |

```
demos/resilient-rates/
├── src/rates/
│   ├── app.py                 # ⭐ composition root (start here)
│   ├── main.py                # entry point / lifecycle
│   ├── config.py              # RatesConfig for demo: section
│   ├── domain.py              # RateQuote value type
│   ├── exceptions.py          # RateProviderError hierarchy
│   ├── di/
│   │   └── provider.py        # RatesProvider (wires cache, pipeline, faults)
│   ├── controllers/
│   │   └── api.py             # REST endpoints (fetch, stats, scenario, demo)
│   ├── repository/
│   │   └── simulated_upstream.py  # SimulatedRatesProvider + FaultController
│   ├── services/
│   │   └── rates_service.py   # RatesService: cache + resilience + stale
│   └── ui/
│       ├── pages.py           # Static serving routes
│       ├── static/app.js      # Vanilla JS client
│       └── views/desk.html    # Single-page console
├── application.yaml           # cache + resilience + web + demo sections
└── tests/                     # scenario-driven resilience tests
```

## REST API

```bash
curl localhost:7073/rates/EUR/USD              # quote via cache → pipeline → stale
curl localhost:7073/stats                      # hits/misses/retries/stale
curl -X POST localhost:7073/scenario/down      # flip upstream health live
curl -X POST localhost:7073/cache/clear        # drop cached quotes
curl -X POST localhost:7073/stampede/USD/JPY   # 10 concurrent fetches → 1 upstream call
curl -X POST localhost:7073/demo               # five-act guided walkthrough
```

## Tests

```bash
uv run pytest demos/resilient-rates/tests -q
```
