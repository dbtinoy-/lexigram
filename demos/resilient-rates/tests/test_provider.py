"""Tests for the simulated rates provider and fault scenarios."""

from __future__ import annotations

from decimal import Decimal
import time

import pytest

from rates.domain import RateQuote
from rates.exceptions import UpstreamTimeoutError, UpstreamUnavailableError
from rates.repository.simulated_upstream import FaultController, Scenario, SimulatedRatesProvider


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

    start = time.monotonic()
    quote = await provider.fetch("EUR/USD")
    elapsed = time.monotonic() - start

    assert quote.source == "upstream"
    # 0.05s sleep minus headroom for scheduling jitter.
    assert elapsed >= 0.04


async def test_unknown_pair_rejected() -> None:
    provider = make_provider(Scenario.HEALTHY)

    with pytest.raises(KeyError):
        await provider.fetch("XYZ/ABC")
