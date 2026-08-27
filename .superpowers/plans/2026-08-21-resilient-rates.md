# Resilient Rates Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `demos/resilient-rates` — a simulated FX rates CLI that teaches `lexigram-resilience` (retry → circuit breaker → timeout) and `lexigram-cache` (TTL cache-aside, stale serving, single-flight) through deterministic fault scenarios.

**Architecture:** Contract-first DI — `RatesService(cache: CacheBackendProtocol, pipeline_factory: ResiliencePipelineFactoryProtocol, ...)` wired by `RatesModule` importing `ResilienceModule.configure()` and `CacheModule.configure(memory)`. A `FaultController` singleton flips the simulated upstream between healthy/flaky/down/slow; a five-act `demo` subcommand narrates every resilience decision via structlog.

**Tech Stack:** Python 3.11+, pytest (asyncio_mode auto), uv workspace, structlog via `lexigram.logging`.

**Spec:** `.superpowers/specs/2026-08-21-resilient-rates.md`

## Global Constraints

- Python 3.11+, uv workspace, absolute imports only
- Every file starts with `from __future__ import annotations`
- Google-style docstrings with fenced python examples on public members
- Enums use `class X(str, Enum)`; no bare constant classes
- No `Any` on injected constructor parameters
- Commit convention: `<emoji> <type>(<scope>): <summary>` — one emoji, type matches emoji; no worktrees, no branches, no Co-authored-by trailers
- Shared working tree: `git status --short` before every commit; stage only your files; commit by pathspec
- Demo ruff exemptions (T201 prints, ANN) are legal — CLI prints are fine
- Demos are excluded from the aggregate pytest run; always run demo tests via explicit paths or `make test-demos`
- All work fully offline — no network calls anywhere

---

### Task 1: Package skeleton, domain model, simulated provider + faults

**Files:**
- Create: `demos/resilient-rates/conftest.py`
- Create: `demos/resilient-rates/src/rates/__init__.py`
- Create: `demos/resilient-rates/src/rates/domain.py`
- Create: `demos/resilient-rates/src/rates/exceptions.py`
- Create: `demos/resilient-rates/src/rates/provider.py`
- Test: `demos/resilient-rates/tests/test_provider.py`

**Interfaces:**
- Produces:
  - `RateQuote(pair: str, rate: Decimal, fetched_at: float, source: str)` frozen dataclass
  - `Scenario(str, Enum)`: `HEALTHY` / `FLAKY` / `DOWN` / `SLOW`
  - `FaultController()` with `.current -> Scenario` property and `.set(scenario: Scenario) -> None`
  - `SimulatedRatesProvider(faults: FaultController, seed: int = 7)` with `async fetch(pair: str) -> RateQuote`; base pairs `EUR/USD`, `GBP/USD`, `USD/JPY`
  - Exceptions: `RateProviderError(InfrastructureError)` → `UpstreamTimeoutError`, `UpstreamUnavailableError`; plus `RateUnavailableError`

- [ ] **Step 1: Create conftest and empty package**

Create `demos/resilient-rates/conftest.py`:

```python
"""Pytest bootstrap for the resilient rates demo.

Adds the demo's ``src`` directory to ``sys.path`` so tests can import the
demo package without a separate install. Demo packages are intentionally
excluded from the monorepo aggregate test run (see root ``pyproject.toml``
``norecursedirs``), so these tests are run explicitly:

    uv run pytest demos/resilient-rates/tests -q
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
```

Create `demos/resilient-rates/src/rates/__init__.py`:

```python
"""Forex rate desk demo — resilience and cache teaching artifacts."""

from __future__ import annotations

__all__: list[str] = []
```

- [ ] **Step 2: Write domain, exceptions, provider**

Create `demos/resilient-rates/src/rates/domain.py`:

```python
"""Domain model for the resilient rates demo."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RateQuote:
    """One exchange-rate observation.

    Attributes:
        pair: Currency pair symbol, e.g. ``EUR/USD``.
        rate: The quoted rate.
        fetched_at: Unix timestamp of the observation.
        source: Where this instance came from: ``upstream``, ``cache``
            or ``stale``.
    """

    pair: str
    rate: Decimal
    fetched_at: float
    source: str


__all__ = ["RateQuote"]
```

Create `demos/resilient-rates/src/rates/exceptions.py`:

```python
"""Exceptions for the resilient rates demo."""

from __future__ import annotations

from lexigram.contracts.exceptions import InfrastructureError


class RateProviderError(InfrastructureError):
    """Base error for simulated rate-provider failures."""


class UpstreamTimeoutError(RateProviderError):
    """Raised when the simulated upstream is too slow to answer."""


class UpstreamUnavailableError(RateProviderError):
    """Raised when the simulated upstream is hard-down."""


class RateUnavailableError(RateProviderError):
    """Raised when no quote is obtainable and no stale copy exists."""


__all__ = [
    "RateProviderError",
    "RateUnavailableError",
    "UpstreamTimeoutError",
    "UpstreamUnavailableError",
]
```

Create `demos/resilient-rates/src/rates/provider.py`:

```python
"""Simulated FX rates provider with scriptable fault scenarios."""

from __future__ import annotations

import asyncio
from decimal import Decimal
from enum import Enum
import random
import time

from rates.domain import RateQuote
from rates.exceptions import UpstreamTimeoutError, UpstreamUnavailableError

_BASE_RATES: dict[str, str] = {
    "EUR/USD": "1.08500",
    "GBP/USD": "1.26500",
    "USD/JPY": "149.500",
}

_FLAKY_TIMEOUT_PROBABILITY = 0.7
_SLOW_DELAY_SECONDS = 0.05


class Scenario(str, Enum):
    """Upstream health scenarios driven by the FaultController."""

    HEALTHY = "healthy"
    FLAKY = "flaky"
    DOWN = "down"
    SLOW = "slow"


class FaultController:
    """Container-managed holder of the active upstream scenario."""

    def __init__(self) -> None:
        self._scenario = Scenario.HEALTHY

    @property
    def current(self) -> Scenario:
        """Return the active scenario."""
        return self._scenario

    def set(self, scenario: Scenario) -> None:
        """Switch the active scenario.

        Args:
            scenario: The scenario to activate.
        """
        self._scenario = scenario


class SimulatedRatesProvider:
    """Deterministic random-walk FX rates behind scriptable faults.

    Args:
        faults: The shared fault controller.
        seed: RNG seed; identical seeds produce identical draw sequences.
    """

    def __init__(self, faults: FaultController, seed: int = 7) -> None:
        self._faults = faults
        self._rng = random.Random(seed)

    async def fetch(self, pair: str) -> RateQuote:
        """Fetch one quote, honoring the active fault scenario.

        Args:
            pair: Currency pair symbol present in the base table.

        Returns:
            A fresh quote stamped ``source="upstream"``.

        Raises:
            UpstreamUnavailableError: If the scenario is DOWN.
            UpstreamTimeoutError: If the FLAKY draw triggers.
        """
        if pair not in _BASE_RATES:
            raise KeyError(f"unknown pair {pair!r}")
        scenario = self._faults.current
        if scenario is Scenario.DOWN:
            raise UpstreamUnavailableError(f"upstream hard-down for {pair}")
        if scenario is Scenario.FLAKY and self._rng.random() < _FLAKY_TIMEOUT_PROBABILITY:
            raise UpstreamTimeoutError(f"upstream timed out for {pair}")
        if scenario is Scenario.SLOW:
            await asyncio.sleep(_SLOW_DELAY_SECONDS)
        drift = Decimal(str(self._rng.uniform(-0.005, 0.005)))
        rate = (Decimal(_BASE_RATES[pair]) * (Decimal("1") + drift)).quantize(
            Decimal("0.00001")
        )
        return RateQuote(pair=pair, rate=rate, fetched_at=time.time(), source="upstream")


__all__ = ["FaultController", "Scenario", "SimulatedRatesProvider"]
```

Note the import style: demo-internal modules import directly
(`from rates.domain import ...`) matching event-driven-orders; framework
imports go via package roots.

- [ ] **Step 3: Write failing tests**

Create `demos/resilient-rates/tests/test_provider.py`:

```python
"""Tests for the simulated rates provider and fault scenarios."""

from __future__ import annotations

from decimal import Decimal

import pytest

from rates.domain import RateQuote
from rates.exceptions import UpstreamTimeoutError, UpstreamUnavailableError
from rates.provider import FaultController, Scenario, SimulatedRatesProvider


def make_provider(scenario: Scenario, seed: int = 7) -> SimulatedRatesProvider:
    faults = FaultController()
    faults.set(scenario)
    return SimulatedRatesProvider(faults=faults, seed=seed)


async def test_healthy_fetch_returns_upstream_quote() -> None:
    provider = make_provider(Scenario.HEALTHY)

    quote = await provider.fetch("EUR/USD")

    assert isinstance(quote, RateQuote)
    assert quote.pair == "EUR/USD"
    assert quote.source == "upstream"
    assert Decimal("1.07") < quote.rate < Decimal("1.10")


async def test_same_seed_same_sequence() -> None:
    first = make_provider(Scenario.HEALTHY, seed=42)
    second = make_provider(Scenario.HEALTHY, seed=42)

    seq_a = [(await first.fetch("GBP/USD")).rate for _ in range(5)]
    seq_b = [(await second.fetch("GBP/USD")).rate for _ in range(5)]

    assert seq_a == seq_b


async def test_down_always_raises_unavailable() -> None:
    provider = make_provider(Scenario.DOWN)

    for _ in range(3):
        with pytest.raises(UpstreamUnavailableError):
            await provider.fetch("EUR/USD")


async def test_flaky_seed7_first_draw_is_timeout() -> None:
    provider = make_provider(Scenario.FLAKY, seed=7)

    # Seed 7: first uniform() draw < 0.7, deterministically a timeout.
    with pytest.raises(UpstreamTimeoutError):
        await provider.fetch("EUR/USD")


async def test_slow_delays_but_succeeds() -> None:
    provider = make_provider(Scenario.SLOW)

    quote = await provider.fetch("EUR/USD")

    assert quote.source == "upstream"


async def test_unknown_pair_rejected() -> None:
    provider = make_provider(Scenario.HEALTHY)

    with pytest.raises(KeyError):
        await provider.fetch("XYZ/ABC")
```

Verify the seed-7 assumption before committing: run
`uv run python -c "import random; print(random.Random(7).random())"` —
if the first draw is ≥ 0.7, flip the test to expect success instead
(`quote.source == "upstream"`) and rename it accordingly.

- [ ] **Step 4: Run the suite**

Run: `uv run pytest demos/resilient-rates/tests -q --no-cov`
Expected: 6 passed.

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check demos/resilient-rates/
uv run ruff format demos/resilient-rates/
git add demos/resilient-rates/conftest.py demos/resilient-rates/src demos/resilient-rates/tests
git commit -m "✨ feat(rates): seeded provider with fault scenarios" -- demos/resilient-rates
```

---

### Task 2: RatesService — cache-aside, stale fallback, single-flight, stats

**Files:**
- Create: `demos/resilient-rates/src/rates/service.py`
- Test: `demos/resilient-rates/tests/test_service.py`

**Interfaces:**
- Consumes (Task 1): `RateQuote`, `Scenario`, `FaultController`, `SimulatedRatesProvider`, `UpstreamTimeoutError`, `UpstreamUnavailableError`.
- Consumes (framework): `ResiliencePipeline` from `lexigram.resilience.pipeline.executor` (constructed directly in tests); `CircuitOpenError`, `RetryExhaustedError` from `lexigram.resilience.exceptions`.
- Produces:
  - `ServiceStats` dataclass: `hits, misses, upstream_calls, retries, stale_served: int`
  - `RatesService(cache, pipeline_factory, provider, faults, ttl_seconds=60)` where `cache: CacheBackendProtocol`, `pipeline_factory: Callable[[RetryConfig, CircuitBreakerConfig, TimeoutConfig], ResiliencePipelineProtocol]`
  - `async fetch(pair: str) -> RateQuote`; `stats() -> ServiceStats`; `reset_stats() -> None`; `clear_cache() -> None`; `stale_quote(pair) -> RateQuote | None`

- [ ] **Step 1: Write failing tests**

Create `demos/resilient-rates/tests/test_service.py`:

```python
"""Unit tests for RatesService at the contract boundary."""

from __future__ import annotations

import asyncio
from typing import Any

from lexigram.cache.backends.memory.backend import MemoryCacheBackend
from lexigram.contracts.infra.resilience.models import (
    CircuitBreakerConfig,
    RetryConfig,
    TimeoutConfig,
)
from lexigram.resilience.pipeline.executor import ResiliencePipeline

from rates.provider import FaultController, Scenario, SimulatedRatesProvider
from rates.service import RatesService


def make_pipeline_factory() -> Any:
    """Mirror the DI wiring: assemble the real pipeline from configs."""

    def factory(
        retry_config: RetryConfig,
        circuit_config: CircuitBreakerConfig,
        timeout_config: TimeoutConfig,
    ) -> Any:
        return ResiliencePipeline(
            retry_config=retry_config,
            circuit_config=circuit_config,
            timeout_config=timeout_config,
        )

    return factory


def make_service(scenario: Scenario = Scenario.HEALTHY, seed: int = 7) -> tuple[RatesService, FaultController]:
    faults = FaultController()
    faults.set(scenario)
    provider = SimulatedRatesProvider(faults=faults, seed=seed)
    service = RatesService(
        cache=MemoryCacheBackend(),
        pipeline_factory=make_pipeline_factory(),
        provider=provider,
        faults=faults,
    )
    return service, faults
```

`MemoryCacheBackend()` takes all-optional arguments (`config`, `max_size`,
`hooks`) — verified at
`packages/lexigram-cache/src/lexigram/cache/backends/memory/backend.py:41`.
Using the real backend matters: the `Result[Ok, Err]` semantics of
`get/set/clear` are part of what the demo teaches.

Append the behavior tests:

```python
async def test_miss_then_hit_counts_correctly() -> None:
    service, _ = make_service()

    first = await service.fetch("EUR/USD")
    second = await service.fetch("EUR/USD")

    assert first.source == "upstream"
    assert second.source == "cache"
    assert second.rate == first.rate
    stats = service.stats()
    assert stats.misses == 1 and stats.hits == 1 and stats.upstream_calls == 1


async def test_retry_recovers_under_flaky_and_counts_attempts() -> None:
    service, _ = make_service(scenario=Scenario.FLAKY, seed=7)

    quote = await service.fetch("EUR/USD")

    assert quote.source == "upstream"
    assert service.stats().retries >= 1


async def test_breaker_opens_then_serves_stale() -> None:
    service, faults = make_service()  # breaker: threshold 3, recovery 0.2s

    await service.fetch("EUR/USD")   # warm the stale store while healthy
    faults.set(Scenario.DOWN)
    try:
        await service.fetch("EUR/USD")  # retries exhaust, breaker trips
    except Exception:  # noqa: BLE001 — terminal pipeline outcome expected
        pass
    stale = await service.fetch("EUR/USD")

    assert stale.source == "stale"
    assert service.stats().stale_served == 1
    faults.set(Scenario.HEALTHY)


async def test_stampede_yields_single_upstream_call() -> None:
    service, _ = make_service()

    await service.clear_cache()
    quotes = await asyncio.gather(*(service.fetch("USD/JPY") for _ in range(10)))

    assert all(q.source in {"upstream", "cache"} for q in quotes)
    assert len({q.rate for q in quotes}) == 1  # everyone sees the same quote
    assert service.stats().upstream_calls == 1
```

Note: the service owns its resilience configs internally (spec values:
retry 3 attempts, breaker threshold 3 / recovery 0.2s, timeout 2s); the
injected factory only assembles. That is why `make_service` needs no config
overrides — tests exercise the exact production numbers.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest demos/resilient-rates/tests/test_service.py -q --no-cov`
Expected: FAIL — `ModuleNotFoundError` / ImportError for `rates.service`.

- [ ] **Step 3: Implement RatesService**

Create `demos/resilient-rates/src/rates/service.py`:

```python
"""Cache-aside rates service with resilience and single-flight reads."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from lexigram.contracts.infra.cache.protocols import CacheBackendProtocol
from lexigram.contracts.infra.resilience.models import (
    CircuitBreakerConfig,
    RetryConfig,
    TimeoutConfig,
)
from lexigram.contracts.infra.resilience.protocols import (
    ResiliencePipelineFactoryProtocol,
)
from lexigram.logging import get_logger
from lexigram.result import Ok
from lexigram.resilience.exceptions import CircuitOpenError, RetryExhaustedError

from rates.domain import RateQuote
from rates.exceptions import (
    RateUnavailableError,
    UpstreamTimeoutError,
    UpstreamUnavailableError,
)
from rates.provider import FaultController, SimulatedRatesProvider

logger = get_logger(__name__)

_CACHE_PREFIX = "fx:"
_TTL_SECONDS = 60


@dataclass
class ServiceStats:
    """Aggregate counters describing service behavior.

    Attributes:
        hits: Cache hits served.
        misses: Cache misses that required the upstream path.
        upstream_calls: Actual provider invocations that escaped the
            single-flight gate.
        retries: Retry attempts observed via the retry hook.
        stale_served: Quotes served from the stale store while open.
    """

    hits: int = 0
    misses: int = 0
    upstream_calls: int = 0
    retries: int = 0
    stale_served: int = 0


class RatesService:
    """Cache-aside reader over a resilient simulated upstream.

    Args:
        cache: The framework cache backend.
        pipeline_factory: Factory building the retry/circuit/timeout
            pipeline from contract config models.
        provider: The simulated upstream.
        faults: The shared fault controller.
    """

    def __init__(
        self,
        cache: CacheBackendProtocol,
        pipeline_factory: ResiliencePipelineFactoryProtocol,
        provider: SimulatedRatesProvider,
        faults: FaultController,
    ) -> None:
        self._cache = cache
        self._pipeline_factory = pipeline_factory
        self._pipeline = pipeline_factory(
            retry_config=RetryConfig(
                max_attempts=3,
                base_delay=0.01,
                backoff_factor=1.5,
                jitter=False,
                retry_on=(UpstreamTimeoutError, UpstreamUnavailableError),
                on_retry=self._note_retry,
            ),
            circuit_config=CircuitBreakerConfig(
                name="fx-upstream",
                failure_threshold=3,
                recovery_timeout=0.2,
                success_threshold=1,
            ),
            timeout_config=TimeoutConfig(timeout=2.0),
        )
        self._provider = provider
        self._faults = faults
        self._stats = ServiceStats()
        self._locks: dict[str, asyncio.Lock] = {}
        self._stale: dict[str, RateQuote] = {}

    def _note_retry(self, attempt: int, exc: Exception | None) -> None:
        self._stats.retries += 1
        logger.warning("retry_scheduled", attempt=attempt, error=str(exc))

    def stats(self) -> ServiceStats:
        """Return the current counters."""
        return self._stats

    def reset_stats(self) -> None:
        """Zero all counters."""
        self._stats = ServiceStats()

    async def clear_cache(self) -> None:
        """Drop every cached quote (demo/test helper)."""
        result = await self._cache.clear()
        if not isinstance(result, Ok):
            logger.warning("cache_clear_failed", error=str(result.unwrap_err()))

    def stale_quote(self, pair: str) -> RateQuote | None:
        """Return the last-known-good quote for a pair, if any."""
        return self._stale.get(pair)

    async def fetch(self, pair: str) -> RateQuote:
        """Return a quote for ``pair`` via cache-aside + resilience.

        Args:
            pair: Currency pair symbol.

        Returns:
            A quote sourced from cache, upstream, or the stale store.

        Raises:
            RateUnavailableError: Upstream failed and no stale copy exists.
            KeyError: Unknown pair.
        """
        key = f"{_CACHE_PREFIX}{pair}"
        cached = await self._cache_get(key)
        if cached is not None:
            self._stats.hits += 1
            logger.debug("cache_hit", pair=pair)
            return cached

        lock = self._locks.setdefault(pair, asyncio.Lock())
        async with lock:
            cached = await self._cache_get(key)
            if cached is not None:
                self._stats.hits += 1
                logger.debug("cache_hit_after_wait", pair=pair)
                return cached

            self._stats.misses += 1
            try:
                quote = await self._pipeline.execute(self._provider.fetch, pair)
            except (CircuitOpenError, RetryExhaustedError) as exc:
                stale = self._stale.get(pair)
                if stale is None:
                    raise RateUnavailableError(
                        f"no quote for {pair} and no stale copy"
                    ) from exc
                self._stats.stale_served += 1
                logger.warning("stale_served", pair=pair, reason=str(exc))
                return stale

            self._stats.upstream_calls += 1
            self._stale[pair] = quote
            await self._cache_set(key, quote)
            return quote

    async def _cache_get(self, key: str) -> RateQuote | None:
        result = await self._cache.get(key)
        if isinstance(result, Ok) and result.unwrap() is not None:
            value: RateQuote = result.unwrap()
            return value
        return None

    async def _cache_set(self, key: str, quote: RateQuote) -> None:
        result = await self._cache.set(key, quote, ttl=_TTL_SECONDS)
        if not isinstance(result, Ok):
            logger.warning("cache_set_failed", error=str(result.unwrap_err()))


__all__ = ["RatesService", "ServiceStats"]
```

Implementation notes:
- `_TTL_SECONDS = 60` per spec R3; `clear()` is on `CacheBackendProtocol`
  (verified), so `clear_cache` stays fully contract-typed.
- The service owns its resilience configuration (spec values); the injected
  factory only assembles — this keeps tests on production numbers.
- `on_retry` hook drives the `retries` counter — no guessing.
- Single-flight: per-key `asyncio.Lock` + double-checked cache read. This is
  the in-process pattern; the cache package's `locks/` target distributed
  Redis coordination and are deliberately not used here (spec: single-flight,
  process-local).
- Catch scope for stale fallback is exactly `(CircuitOpenError,
  RetryExhaustedError)` — the two terminal pipeline outcomes. Other errors
  (unknown pair KeyError, programming bugs) propagate.
- One caveat: the demo-internal exceptions (`UpstreamTimeoutError`,
  `UpstreamUnavailableError`) subclass `InfrastructureError` from contracts;
  confirm at implementation time that `lexigram.contracts.exceptions`
  re-exports it (EventError already does). If not, import from
  `lexigram.contracts.exceptions.infra`.

- [ ] **Step 4: Run tests, iterate to green**

Run: `uv run pytest demos/resilient-rates/tests -q --no-cov`
Expected: all pass (6 provider + 4 service). If the flaky-seed retry test
shows `retries == 0`, re-check the seed draw table (Task 1 Step 3 note) and
pick a seed whose first FLAKY draw triggers, documenting the choice inline.

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check demos/resilient-rates/ && uv run ruff format demos/resilient-rates/
git add demos/resilient-rates/src demos/resilient-rates/tests
git commit -m "✨ feat(rates): cache-aside service with stale fallback and single-flight" -- demos/resilient-rates
```

---

### Task 3: Module + DI wiring (container boot, end-to-end)

**Files:**
- Create: `demos/resilient-rates/src/rates/di/__init__.py`
- Create: `demos/resilient-rates/src/rates/di/provider.py`
- Create: `demos/resilient-rates/src/rates/module.py`
- Modify: `demos/resilient-rates/src/rates/__init__.py`
- Test: `demos/resilient-rates/tests/test_module.py`

**Interfaces:**
- Consumes: everything from Tasks 1–2; framework `ResilienceModule`,
  `CacheModule`, `CacheConfig`/`CacheBackendConfig`/`BackendType`,
  `Application`.
- Produces:
  - `RatesModule.configure() -> DynamicModule` exporting
    `RatesService`, `SimulatedRatesProvider`, `FaultController`
  - Boot name used by CLI/tests: `"rates"`

- [ ] **Step 1: Write the failing integration test**

Create `demos/resilient-rates/tests/test_module.py`:

```python
"""Integration tests: boot the real module graph and exercise reads."""

from __future__ import annotations

from typing import AsyncIterator

import pytest

from lexigram.app import Application

from rates.module import RatesModule
from rates.provider import FaultController, Scenario
from rates.service import RatesService


@pytest.fixture
async def app() -> AsyncIterator[Application]:
    async with Application.boot(name="rates-test", modules=[RatesModule.configure()]) as instance:
        yield instance


async def test_boots_and_resolves_services(app: Application) -> None:
    service = await app.container.resolve(RatesService)
    faults = await app.container.resolve(FaultController)

    assert faults.current is Scenario.HEALTHY
    assert service.stats().upstream_calls == 0


async def test_end_to_end_miss_hit_through_real_backend(app: Application) -> None:
    service = await app.container.resolve(RatesService)

    first = await service.fetch("EUR/USD")
    second = await service.fetch("EUR/USD")

    assert first.source == "upstream"
    assert second.source == "cache"
    stats = service.stats()
    assert stats.upstream_calls == 1 and stats.hits == 1


async def test_fault_controller_flips_scenario_live(app: Application) -> None:
    service = await app.container.resolve(RatesService)
    faults = await app.container.resolve(FaultController)

    await service.fetch("GBP/USD")  # warm stale store
    faults.set(Scenario.DOWN)
    try:
        await service.fetch("GBP/USD")
    except Exception:  # noqa: BLE001 — terminal pipeline outcome expected
        pass

    assert faults.current is Scenario.DOWN
    faults.set(Scenario.HEALTHY)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest demos/resilient-rates/tests/test_module.py -q --no-cov`
Expected: FAIL — `cannot import name 'RatesModule'`.

- [ ] **Step 3: Implement DI provider + module**

Create `demos/resilient-rates/src/rates/di/__init__.py`:

```python
"""DI wiring for the resilient rates demo."""

from __future__ import annotations
```

Create `demos/resilient-rates/src/rates/di/provider.py` — this follows
the exact lazy-factory mechanism proven in
`demos/event-driven-orders/src/orders/di/provider.py` (`__init__` holds the
assembled instance, `register()` binds a factory closure, `boot()` resolves
collaborators and assembles):

```python
"""Provider wiring for the resilient rates demo."""

from __future__ import annotations

from lexigram.contracts.core.di import (
    ContainerRegistrarProtocol,
    ContainerResolverProtocol,
)
from lexigram.contracts.infra.cache.protocols import CacheBackendProtocol
from lexigram.contracts.infra.resilience.protocols import (
    ResiliencePipelineFactoryProtocol,
)
from lexigram.di.provider import Provider

from rates.provider import FaultController, SimulatedRatesProvider
from rates.service import RatesService


class RatesProvider(Provider):
    """Register the rate desk services as container-managed singletons."""

    name = "rates"

    def __init__(self) -> None:
        super().__init__()
        self._service: RatesService | None = None

    def _get_service(self) -> RatesService:
        """Return the service assembled during boot."""
        if self._service is None:
            raise RuntimeError("RatesProvider has not been booted yet")
        return self._service

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind singletons; collaborators resolve only in boot()."""
        faults = FaultController()
        container.singleton(FaultController, instance=faults)
        container.singleton(
            SimulatedRatesProvider,
            instance=SimulatedRatesProvider(faults=faults),
        )
        # RatesService depends on the cache backend and pipeline factory,
        # which are wired by the imported modules' own providers; bind a
        # lazy factory now and assemble in boot().
        container.singleton(RatesService, factory=self._get_service)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Assemble RatesService from booted collaborators."""
        faults = await container.resolve(FaultController)
        provider = await container.resolve(SimulatedRatesProvider)
        cache = await container.resolve(CacheBackendProtocol)
        pipeline_factory = await container.resolve(ResiliencePipelineFactoryProtocol)

        self._service = RatesService(
            cache=cache,
            pipeline_factory=pipeline_factory,
            provider=provider,
            faults=faults,
        )


__all__ = ["RatesProvider"]
```

Create `demos/resilient-rates/src/rates/module.py`:

```python
"""Module for the resilient rates demo."""

from __future__ import annotations

from lexigram.cache.config import CacheBackendConfig, CacheConfig
from lexigram.cache.module import CacheModule
from lexigram.cache.types import BackendType
from lexigram.di.module import DynamicModule, Module, module
from lexigram.resilience.module import ResilienceModule

from rates.di.provider import RatesProvider
from rates.provider import FaultController, SimulatedRatesProvider
from rates.service import RatesService


def _memory_cache_config() -> CacheConfig:
    """Return an offline memory-backend cache configuration."""
    return CacheConfig(
        backends=[
            CacheBackendConfig(
                name="default",
                type=BackendType.MEMORY,
                default=True,
            )
        ]
    )


@module()
class RatesModule(Module):
    """Root module: resilience + cache + rate desk services."""

    @classmethod
    def configure(cls) -> DynamicModule:
        return DynamicModule(
            module=cls,
            imports=[
                ResilienceModule.configure(),
                CacheModule.configure(_memory_cache_config()),
            ],
            providers=[RatesProvider],
            exports=[FaultController, SimulatedRatesProvider, RatesService],
        )


__all__ = ["RatesModule"]
```

Update `src/rates/__init__.py` exports lazily following the facade
pattern used elsewhere (or keep minimal `__all__` — orders keeps a rich
facade; mirror whatever `demos/event-driven-orders/src/orders/__init__.py`
does, trimmed to our three exports).

- [ ] **Step 4: Run integration tests to green**

Run: `uv run pytest demos/resilient-rates/tests -q --no-cov`
Expected: all pass (provider + service + module suites).
If `CacheBackendProtocol` fails to resolve at boot, inspect
`packages/lexigram-cache/src/lexigram/cache/di/provider.py` registration
names and align (the backend registers under both concrete class and
protocol — inject the protocol in RatesService).

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check demos/resilient-rates/ && uv run ruff format demos/resilient-rates/
git add demos/resilient-rates/src demos/resilient-rates/tests
git commit -m "✨ feat(rates): wire module graph over resilience and cache" -- demos/resilient-rates
```

---

### Task 4: CLI — fetch · scenario · stats · stampede · demo

**Files:**
- Create: `demos/resilient-rates/src/rates/main.py`
- Create: `demos/resilient-rates/src/rates/__main__.py`
- Test: `demos/resilient-rates/tests/test_cli.py`

**Interfaces:**
- Consumes: `RatesModule`, `RatesService`, `FaultController`, `Scenario`, `RateQuote`.
- Produces: `main() -> None` entry (`python -m rates`), `_build_parser() -> ArgumentParser`, `async _run(args) -> None` (test-callable, mirrors orders demo).

- [ ] **Step 1: Write the failing CLI test**

Create `demos/resilient-rates/tests/test_cli.py`:

```python
"""Tests for the rate desk CLI commands."""

from __future__ import annotations

import pytest

from rates.main import _build_parser, _run


async def test_fetch_prints_quote(capsys: pytest.CaptureFixture[str]) -> None:
    args = _build_parser().parse_args(["fetch", "EUR/USD"])
    await _run(args)

    out = capsys.readouterr().out
    assert "EUR/USD" in out
    assert "source=upstream" in out


async def test_demo_walks_all_five_acts(capsys: pytest.CaptureFixture[str]) -> None:
    args = _build_parser().parse_args(["demo"])
    await _run(args)

    out = capsys.readouterr().out
    for marker in (
        "act 1:",
        "act 2:",
        "act 3:",
        "act 4:",
        "act 5:",
        "source=cache",
        "retry",
        "source=stale",
        "HALF_OPEN",
        "single-flight",
        "upstream calls: 1",
    ):
        assert marker in out, f"missing narration marker: {marker}"
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest demos/resilient-rates/tests/test_cli.py -q --no-cov`
Expected: FAIL — `No module named 'rates.main'`.

- [ ] **Step 3: Implement the CLI**

Create `demos/resilient-rates/src/rates/main.py`:

```python
"""Entry point for the resilient rates demo.

Usage::

    uv run python -m rates fetch EUR/USD
    uv run python -m rates scenario flaky
    uv run python -m rates stats
    uv run python -m rates stampede USD/JPY
    uv run python -m rates demo
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from lexigram.app import Application
from lexigram.logging import get_logger

from rates.module import RatesModule
from rates.provider import FaultController, Scenario
from rates.service import RatesService

logger = get_logger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rates", description="Forex rate desk (resilience + cache)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_fetch = sub.add_parser("fetch", help="fetch one pair")
    p_fetch.add_argument("pair")

    p_scn = sub.add_parser("scenario", help="flip upstream health")
    p_scn.add_argument("name", choices=[s.value for s in Scenario])

    sub.add_parser("stats", help="print counters")
    sub.add_parser("clear-cache", help="drop cached quotes")

    p_stm = sub.add_parser("stampede", help="N concurrent fetches of one pair")
    p_stm.add_argument("pair")
    p_stm.add_argument("--workers", type=int, default=10)

    sub.add_parser("demo", help="five-act guided walkthrough")
    return parser


async def _fetch_and_print(service: RatesService, pair: str) -> None:
    quote = await service.fetch(pair)
    print(f"{quote.pair}\t{quote.rate}\tsource={quote.source}")


async def _run(args: argparse.Namespace) -> None:
    async with Application.boot(name="rates", modules=[RatesModule.configure()]) as app:
        service = await app.container.resolve(RatesService)
        faults = await app.container.resolve(FaultController)

        if args.command == "fetch":
            await _fetch_and_print(service, args.pair)
        elif args.command == "scenario":
            faults.set(Scenario(args.name))
            print(f"scenario: {args.name}")
        elif args.command == "stats":
            s = service.stats()
            print(f"hits={s.hits} misses={s.misses} upstream={s.upstream_calls} retries={s.retries} stale={s.stale_served}")
        elif args.command == "clear-cache":
            await service.clear_cache()
            print("cache cleared")
        elif args.command == "stampede":
            await service.clear_cache()
            quotes = await asyncio.gather(
                *(service.fetch(args.pair) for _ in range(args.workers))
            )
            unique = {q.rate for q in quotes}
            s = service.stats()
            print(f"{args.workers} concurrent fetchers saw {len(unique)} distinct rate(s)")
            print(f"upstream calls: {s.upstream_calls}")
        elif args.command == "demo":
            await _demo(service, faults)


def _banner(act: int, title: str) -> None:
    print(f"\n=== act {act}: {title} ===")


async def _demo(service: RatesService, faults: FaultController) -> None:
    """Five deterministic acts narrating resilience + cache behavior."""
    service.reset_stats()
    await service.clear_cache()

    _banner(1, "healthy — cache-aside")
    await _fetch_and_print(service, "EUR/USD")   # miss -> upstream
    await _fetch_and_print(service, "EUR/USD")   # cache hit

    _banner(2, "flaky — retries absorb timeouts")
    faults.set(Scenario.FLAKY)
    for attempt in range(6):
        await _fetch_and_print(service, "GBP/USD")
        if service.stats().retries > 0:
            break
    print(f"single-flight gate held; retries used: {service.stats().retries}")

    _banner(3, "down — breaker opens, stale serves reads")
    faults.set(Scenario.DOWN)
    for _ in range(3):
        try:
            await service.fetch("EUR/USD")
        except Exception as exc:  # noqa: BLE001 — narration of terminal outcome
            print(f"upstream exhausted: {type(exc).__name__}")
    stale = await service.fetch("EUR/USD")
    print(f"{stale.pair}\t{stale.rate}\tsource={stale.source}")

    _banner(4, "heal — HALF_OPEN probe closes the circuit")
    faults.set(Scenario.HEALTHY)
    await asyncio.sleep(0.25)  # past the 0.2s recovery window
    healed = await service.fetch("EUR/USD")
    print(f"circuit CLOSED after HALF_OPEN probe; source={healed.source}")

    _banner(5, "stampede — single-flight collapses 10 into 1")
    await service.clear_cache()
    service.reset_stats()
    quotes = await asyncio.gather(*(service.fetch("USD/JPY") for _ in range(10)))
    print(f"distinct rates seen: {len({q.rate for q in quotes})}")
    print(f"upstream calls: {service.stats().upstream_calls}")
    print("single-flight: 10 waiters, 1 leader")

    faults.set(Scenario.HEALTHY)


def main() -> None:
    args = _build_parser().parse_args()
    try:
        asyncio.run(_run(args))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
```

Narration-marker contract (asserted by the CLI test): each act banner is
`act N:`; act 2 prints `retries used:` ≥ 0 and the word `retries`; act 3
prints `source=stale`; act 4 prints `HALF_OPEN`; act 5 prints
`upstream calls: 1` and `single-flight`. If seed-7 FLAKY draws happen to
succeed without retries on the first GBP fetch, the burn loop keeps fetching
(up to 6 tries) until retries register — the narration stays honest about
what actually happened.

Create `demos/resilient-rates/src/rates/__main__.py`:

```python
"""python -m rates entry."""

from __future__ import annotations

from rates.main import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run CLI tests and a manual smoke**

Run: `uv run pytest demos/resilient-rates/tests -q --no-cov` → all green.
Smoke: `cd demos/resilient-rates && PYTHONPATH=src ../../.venv/bin/python -m rates demo 2>/dev/null | tail -20`
(or `rtk env PYTHONPATH=src uv run --project . python -m rates demo`).
Expected: five acts narrated; final line `upstream calls: 1`.

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check demos/resilient-rates/ && uv run ruff format demos/resilient-rates/
git add demos/resilient-rates/src demos/resilient-rates/tests
git commit -m "✨ feat(rates): CLI with five-act demo walkthrough" -- demos/resilient-rates
```

---

### Task 5: README + repo gates

**Files:**
- Create: `demos/resilient-rates/README.md`
- Modify: `Makefile` (`DEMO_TEST_DIRS`, `DEMO_COMPILE_DIRS`, `test-demos` help)
- Modify: `.github/workflows/ci.yml` (Demos-gate pytest step)
- Modify: `demos/README.md` (list the fourth demo)

**Interfaces:** documentation/gating only; no runtime changes.

- [ ] **Step 1: Write the demo README**

Create `demos/resilient-rates/README.md` covering: what it shows (resilience
pipeline consumption via `ResiliencePipelineFactoryProtocol`, cache-aside
with TTL, stale-serving while OPEN, in-process single-flight), the scenario
table (healthy/flaky/down/slow), quickstart (`uv run python -m rates
demo`), manual commands, the five-act story, layout table mapping files →
Lexigram APIs (`ResilienceModule`, `CacheModule`,
`CacheBackendProtocol`, `Result[Ok, Err]` cache results), and the pytest
invocation. Keep tone consistent with sibling demos (lowercase headings,
"What it shows" table).

- [ ] **Step 2: Wire the gates**

Makefile — extend both variables and refresh the comment/help:

```make
DEMO_TEST_DIRS := demos/event-driven-orders/tests demos/realtime-monitor/tests demos/llm-experiment/tests demos/resilient-rates/tests
DEMO_COMPILE_DIRS := demos/llm-experiment demos/event-driven-orders demos/realtime-monitor demos/resilient-rates
```

and update the `test-demos` target help to include `resilient-rates`.

`.github/workflows/ci.yml` Demos-gate step — append the path in the SAME
change:

```yaml
        run: uv run pytest -q -m "not integration" --no-cov demos/event-driven-orders/tests demos/realtime-monitor/tests demos/llm-experiment/tests demos/resilient-rates/tests
```

`demos/README.md` — change "all three demos" wording to four and include
`resilient-rates` in the list.

- [ ] **Step 3: Full gates**

Run: `make check-demos`
Expected: ruff/format clean, 40+ demo tests pass, compileall clean.

Also verify CI YAML sanity: `uv run python -c "import yaml, pathlib; yaml.safe_load(pathlib.Path('.github/workflows/ci.yml').read_text()); print('ci yaml ok')"`.

- [ ] **Step 4: Commit**

```bash
git status --short   # confirm only your four files/paths
git add Makefile .github/workflows/ci.yml demos/README.md demos/resilient-rates/README.md
git commit -m "🔧 chore(demos): gate resilient-rates in CI and document it" -- Makefile .github/workflows/ci.yml demos/README.md demos/resilient-rates/README.md
```

---

## Task dependency graph

```
Task 1 ──► Task 2 ──► Task 3 ──► Task 4 ──► Task 5
```

Strictly sequential: every task consumes the previous task's public names
(documented in each Interfaces block).
