"""Cache-aside rates service with resilience and single-flight reads."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any

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
        key = f"{_CACHE_PREFIX}{pair}"
        logger.debug("fetch_started", pair=pair, scenario=self._faults.current.value)
        cached = await self._cache_get(key)
        if cached is not None:
            self._stats.hits += 1
            logger.debug("cache_hit", pair=pair)
            return Ok(self._as_cache_hit(cached))

        lock = self._locks.setdefault(pair, asyncio.Lock())
        async with lock:
            cached = await self._cache_get(key)
            if cached is not None:
                self._stats.hits += 1
                logger.debug("cache_hit_after_wait", pair=pair)
                return Ok(self._as_cache_hit(cached))

            self._stats.misses += 1
            try:
                quote = await self._pipeline.execute(self._provider.fetch, pair)
            except (CircuitOpenError, RetryExhaustedError) as exc:
                # Any terminal pipeline failure falls back to the stale tier
                # when a last-known-good copy exists; without one, the outage
                # surfaces to the caller.
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

            self._stats.upstream_calls += 1
            self._stale[pair] = quote
            await self._cache_set(key, quote)
            return Ok(quote)

    def _as_cache_hit(self, quote: RateQuote) -> RateQuote:
        """Re-stamp a stored quote with its serve-time provenance.

        Args:
            quote: The quote decoded from the cache backend.

        Returns:
            An equal quote whose ``source`` reads ``"cache"``.
        """
        return replace(quote, source="cache")

    async def _cache_get(self, key: str) -> RateQuote | None:
        """Read a quote from the cache, decoding the JSON-safe payload.

        Args:
            key: Full cache key.

        Returns:
            The reconstructed quote, or None on miss.
        """
        result = await self._cache.get(key)
        if isinstance(result, Ok) and result.unwrap() is not None:
            raw: dict[str, Any] = result.unwrap()
            return RateQuote(
                pair=str(raw["pair"]),
                rate=Decimal(str(raw["rate"])),
                fetched_at=float(raw["fetched_at"]),
                source=str(raw["source"]),
            )
        return None

    async def _cache_set(self, key: str, quote: RateQuote) -> None:
        """Write a quote to the cache as a JSON-safe payload.

        Backends serialize values (the memory store round-trips through
        JSON), so the service owns an explicit dict codec here.

        Args:
            key: Full cache key.
            quote: The quote to encode and store.
        """
        payload = {
            "pair": quote.pair,
            "rate": str(quote.rate),
            "fetched_at": quote.fetched_at,
            "source": quote.source,
        }
        # TTL is owned by the backend (cache.backends[].default_ttl).
        result = await self._cache.set(key, payload)
        if not isinstance(result, Ok):
            logger.warning("cache_set_failed", error=str(result.unwrap_err()))


__all__ = ["RatesService", "ServiceStats"]
