"""Unit tests for RatesService at the contract boundary."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import Any

import pytest

from lexigram.cache.backends.memory.backend import MemoryCacheBackend
from lexigram.contracts.infra.resilience.models import (
    CircuitBreakerConfig,
    RetryConfig,
    TimeoutConfig,
)
from lexigram.resilience.pipeline.executor import ResiliencePipeline

from rates.exceptions import RateUnavailableError
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
    # Seed 1 draw table: first FLAKY draw 0.1344 triggers a timeout, second
    # draw 0.8474 succeeds — exactly one retry, deterministically.
    service, _ = make_service(scenario=Scenario.FLAKY, seed=1)

    quote = await service.fetch("EUR/USD")

    assert quote.source == "upstream"
    assert service.stats().retries >= 1


async def test_breaker_opens_then_serves_stale() -> None:
    """Terminal outage outcomes fall back to the warm stale copy."""

    def single_fault_factory(
        retry_config: RetryConfig,
        circuit_config: CircuitBreakerConfig,
        timeout_config: TimeoutConfig,
    ) -> ResiliencePipeline:
        # Trip on the first failed execution and keep the circuit OPEN for
        # the whole test so both terminal outcomes are observably stable.
        return ResiliencePipeline(
            retry_config=retry_config,
            circuit_config=replace(
                circuit_config,
                failure_threshold=1,
                recovery_timeout=60.0,
            ),
            timeout_config=timeout_config,
        )

    faults = FaultController()
    provider = SimulatedRatesProvider(faults=faults, seed=7)
    service = RatesService(
        cache=MemoryCacheBackend(),
        pipeline_factory=single_fault_factory,
        provider=provider,
        faults=faults,
    )

    await service.fetch("EUR/USD")  # warm the stale store while healthy
    await service.clear_cache()  # drop the cached quote so DOWN reaches the pipeline
    faults.set(Scenario.DOWN)

    exhausted = await service.fetch("EUR/USD")  # retries exhausted -> stale
    open_circuit = await service.fetch("EUR/USD")  # breaker OPEN -> stale

    assert exhausted.source == "stale"
    assert open_circuit.source == "stale"
    assert service.stats().stale_served == 2

    faults.set(Scenario.HEALTHY)


async def test_production_breaker_stops_calling_upstream_while_serving_stale() -> None:
    # Production numbers (threshold=3, recovery=0.2): repeated DOWN reads
    # must eventually trip the circuit — observable as upstream_calls
    # plateauing while every read keeps being served from the stale tier.
    faults = FaultController()
    provider = SimulatedRatesProvider(faults=faults, seed=7)
    service = RatesService(
        cache=MemoryCacheBackend(),
        pipeline_factory=make_pipeline_factory(),
        provider=provider,
        faults=faults,
    )

    await service.fetch("EUR/USD")  # warm the stale tier while healthy
    await service.clear_cache()
    faults.set(Scenario.DOWN)

    upstream_sequence: list[int] = []
    for _ in range(5):
        quote = await service.fetch("EUR/USD")
        assert quote.source == "stale"
        upstream_sequence.append(service.stats().upstream_calls)

    assert service.stats().stale_served == 5
    assert upstream_sequence[-1] == upstream_sequence[-2]  # plateau: breaker OPEN
    assert service.stats().retries >= 1  # retries were attempted before tripping

    faults.set(Scenario.HEALTHY)


async def test_down_without_stale_copy_raises() -> None:
    """A never-warmed pair has no stale tier: the outage surfaces."""

    service, faults = make_service()

    faults.set(Scenario.DOWN)

    with pytest.raises(RateUnavailableError):
        await service.fetch("GBP/USD")

    assert service.stats().stale_served == 0

    faults.set(Scenario.HEALTHY)


async def test_stampede_yields_single_upstream_call() -> None:
    service, _ = make_service()

    await service.clear_cache()
    quotes = await asyncio.gather(*(service.fetch("USD/JPY") for _ in range(10)))

    assert all(q.source in {"upstream", "cache"} for q in quotes)
    assert len({q.rate for q in quotes}) == 1  # everyone sees the same quote
    assert service.stats().upstream_calls == 1
