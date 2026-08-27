"""Cache-aside rates service with resilience and single-flight reads.

Convention followed: **Service pattern** — this module owns the core
business logic for the rate desk.  It composes three Lexigram
subsystems:

1. **Cache-aside** — ``StampedeProtectedCache`` wraps the framework's
   ``CacheBackendProtocol`` with per-key single-flight locks.  Reads
   check the cache first; misses compute through the pipeline and write
   the result back.

2. **Resilience pipeline** — ``ResiliencePipelineFactoryProtocol`` builds
   a retry → circuit breaker → timeout pipeline from contract config
   models.  Terminal failures (retries exhausted or circuit open) fall
   back to the stale tier.

3. **Stale tier** — an in-memory dict of last-known-good quotes keyed by
   pair.  Served when the circuit is OPEN and the cache is cold.

All domain failures return ``Result[RateQuote, RateUnavailableError]``
— infrastructure exceptions propagate naturally.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from lexigram.cache.service.stampede import StampedeProtectedCache
from lexigram.contracts.infra.cache import CacheBackendProtocol
from lexigram.contracts.infra.resilience import ResiliencePipelineFactoryProtocol
from lexigram.logging import get_logger
from lexigram.resilience import (
    CircuitBreakerConfig,
    CircuitOpenError,
    RetryConfig,
    RetryExhaustedError,
    TimeoutConfig,
)
from lexigram.result import Err, Ok, Result
from rates.domain import RateQuote
from rates.exceptions import (
    RateUnavailableError,
    UpstreamTimeoutError,
    UpstreamUnavailableError,
)
from rates.repository.simulated_upstream import FaultController, SimulatedRatesProvider

logger = get_logger(__name__)

_CACHE_PREFIX = "fx:"


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

    Single-flight collapsing delegates to the framework's
    :class:`StampedeProtectedCache`, which also owns storage of the cached
    envelope; TTL ownership belongs to the cache backend configuration
    (``cache.backends[].default_ttl`` in ``application.yaml``).

    Args:
        cache: The framework cache backend.
        protection: Stampede protection wrapping the cache.
        pipeline_factory: Factory building the retry/circuit/timeout
            pipeline from contract config models.
        provider: The simulated upstream.
        faults: The shared fault controller.
        cache_ttl: Optional TTL override (seconds).  Defaults to 300.
    """

    def __init__(
        self,
        cache: CacheBackendProtocol,
        protection: StampedeProtectedCache,
        pipeline_factory: ResiliencePipelineFactoryProtocol,
        provider: SimulatedRatesProvider,
        faults: FaultController,
        cache_ttl: int | None = None,
    ) -> None:
        self._cache = cache
        self._protection = protection
        self._cache_ttl = cache_ttl if cache_ttl is not None else 300
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
        self._stale: dict[str, RateQuote] = {}

    def _note_retry(self, attempt: int, exc: Exception | None) -> None:
        """Hook called by the retry policy on each attempt."""
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

    async def fetch(self, pair: str) -> Result[RateQuote, RateUnavailableError]:
        """Return a quote for ``pair`` via cache-aside + resilience.

        The read path is:

        1. ``StampedeProtectedCache.get_or_compute`` checks the cache.
        2. On miss, ``compute()`` runs through the resilience pipeline.
        3. The pipeline calls ``SimulatedRatesProvider.fetch()``.
        4. On terminal failure, the stale tier is checked.
        5. If no stale copy exists, ``Err(RateUnavailableError)``.

        Args:
            pair: Currency pair symbol.

        Returns:
            ``Ok(quote)`` sourced from cache, upstream, or the stale
            store; ``Err(RateUnavailableError)`` when the pipeline fails
            terminally (retries exhausted / circuit open) and no stale
            copy exists.
        """
        logger.debug("fetch_started", pair=pair, scenario=self._faults.current.value)

        leader = {"computed": False}

        async def compute() -> dict[str, object]:
            leader["computed"] = True
            quote = await self._pipeline.execute(self._provider.fetch, pair)
            return quote.to_payload()

        try:
            payload = await self._protection.get_or_compute(
                f"{_CACHE_PREFIX}{pair}",
                compute,
                ttl=self._cache_ttl,
            )
        except (CircuitOpenError, RetryExhaustedError) as exc:
            stale = self._stale.get(pair)
            if stale is None:
                return Err(
                    RateUnavailableError(
                        f"upstream unavailable for {pair} and no stale copy"
                    )
                )
            self._stats.stale_served += 1
            logger.warning("stale_served", pair=pair, reason=str(exc))
            return Ok(replace(stale, source="stale"))

        quote = RateQuote.from_payload(payload)
        if leader["computed"]:
            self._stats.misses += 1
            self._stats.upstream_calls += 1
            self._stale[pair] = quote
            logger.debug("upstream_served", pair=pair)
            return Ok(quote)

        self._stats.hits += 1
        logger.debug("cache_hit", pair=pair)
        return Ok(replace(quote, source="cache"))


__all__ = ["RatesService", "ServiceStats"]
