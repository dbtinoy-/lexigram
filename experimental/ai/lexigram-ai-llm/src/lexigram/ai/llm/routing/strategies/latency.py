"""Latency-Optimized Routing Strategy."""

from __future__ import annotations

import collections
from typing import Any

from lexigram.ai.llm.routing.config import LLMConfig, ProviderConfig
from lexigram.ai.llm.routing.strategies.base import (
    _attempt_provider,
    _gen_defaults,
    _handle_free_failure,
)
from lexigram.ai.llm.routing.types import InferenceResult
from lexigram.ai.llm.types import AIError
from lexigram.contracts.ai import LLMClientProtocol
from lexigram.contracts.ai.routing import QuotaBackendProtocol
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class LatencyOptimizedStrategy:
    """Route to the provider with the lowest recent average latency.

    Maintains a rolling window of latency samples per provider.
    Providers with no samples yet are tried first (exploration) to
    bootstrap the statistics.

    When ``skip_unhealthy`` is enabled, providers whose last
    ``health_check()`` returned ``UNHEALTHY`` are skipped.

    Args:
        window_size: Number of recent samples to keep per provider.
        skip_unhealthy: Run ``health_check()`` and skip unhealthy providers.
        health_timeout: Timeout in seconds for each health check call.
    """

    def __init__(
        self,
        window_size: int = 20,
        skip_unhealthy: bool = True,
        health_timeout: float = 3.0,
    ) -> None:
        self._window_size = window_size
        self._skip_unhealthy = skip_unhealthy
        self._health_timeout = health_timeout
        self._samples: dict[str, collections.deque[float]] = {}

    def record_latency(self, provider: str, latency_ms: float) -> None:
        """Manually record a latency sample."""
        dq = self._samples.setdefault(
            provider,
            collections.deque(maxlen=self._window_size),
        )
        dq.append(latency_ms)

    def _avg_latency(self, provider: str) -> float:
        """Return average latency; -1.0 if no data (explore first)."""
        dq = self._samples.get(provider)
        if not dq:
            return -1.0
        return sum(dq) / len(dq)

    async def execute(
        self,
        *,
        providers: list[ProviderConfig],
        clients: dict[str, LLMClientProtocol],
        quota: QuotaBackendProtocol,
        config: LLMConfig,
        messages: list[Any],
        kwargs: dict[str, Any],
    ) -> tuple[InferenceResult | None, list[str], int]:
        temperature, max_tokens = _gen_defaults(config, kwargs)

        # Partition providers: unknown latency first (explore), then sort by avg.
        eligible: list[ProviderConfig] = [
            p for p in providers if p.enabled and clients.get(p.key) is not None
        ]

        # Skip unhealthy providers when enabled.
        if self._skip_unhealthy:
            healthy: list[ProviderConfig] = []
            for p in eligible:
                client = clients[p.key]
                if hasattr(client, "health_check"):
                    try:
                        hc = await client.health_check(timeout=self._health_timeout)
                        if hasattr(hc, "status") and str(hc.status) == "unhealthy":
                            logger.info(
                                "latency_optimized: skipping unhealthy provider=%s",
                                p.name,
                            )
                            continue
                    except (OSError, ConnectionError, TimeoutError, RuntimeError):
                        logger.debug(
                            "latency_optimized: health_check failed for %s, including anyway",
                            p.name,
                        )
                healthy.append(p)
            # Fall back to full list if all are unhealthy.
            if healthy:
                eligible = healthy

        unknown = [p for p in eligible if self._avg_latency(p.key) < 0]
        known = [p for p in eligible if self._avg_latency(p.key) >= 0]
        known.sort(key=lambda p: self._avg_latency(p.key))

        ordered = unknown + known

        providers_tried: list[str] = []
        total_attempts = 0

        for pcfg in ordered:
            client = clients[pcfg.key]
            providers_tried.append(pcfg.name)

            if await quota.is_exhausted(pcfg.key):
                continue

            model = pcfg.model
            total_attempts += 1
            try:
                result = await _attempt_provider(
                    client=client,
                    provider_name=pcfg.name,
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                await quota.increment(pcfg.key)
                self.record_latency(pcfg.key, result.latency_ms)
                logger.info(
                    "latency_optimized: success provider=%s model=%s "
                    "latency_ms=%.0f avg_latency=%.0f",
                    pcfg.name,
                    model,
                    result.latency_ms,
                    self._avg_latency(pcfg.key),
                )
                return result, providers_tried, total_attempts
            except AIError as exc:
                await _handle_free_failure(
                    exc=exc,
                    provider_key=pcfg.key,
                    model=model,
                    quota=quota,
                    cooldown_seconds=config.quota.cooldown_seconds,
                )

        return None, providers_tried, total_attempts
