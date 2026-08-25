"""Cache-aside rates service with resilience and single-flight reads."""

from __future__ import annotations

from dataclasses import dataclass, replace

from lexigram.cache.service.stampede import StampedeProtectedCache
from lexigram.contracts.core.result import Err, Ok, Result
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
from lexigram.resilience.exceptions import CircuitOpenError, RetryExhaustedError
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
        pipeline_factory: Factory building the retry/circuit/timeout
            pipeline from contract config models.
        provider: The simulated upstream.
        faults: The shared fault controller.
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

        Args:
            pair: Currency pair symbol.

        Returns:
            ``Ok(quote)`` sourced from cache, upstream, or the stale
            store; ``Err(RateUnavailableError)`` when the pipeline fails
            terminally (retries exhausted / circuit open) and no stale
            copy exists.
        """
        logger.debug("fetch_started", pair=pair, scenario=self._faults.current.value)

        # The cell marks whether THIS call ran the compute coroutine; if it
        # did not, the value came from the framework's single-flight gate
        # (either a stored copy or a co-running leader).
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
            # Terminal pipeline failure falls back to the stale tier when a
            # last-known-good copy exists; without one, the outage surfaces.
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
