"""Simulated FX rates provider with scriptable fault scenarios.

Convention followed: **Repository pattern** — ``SimulatedRatesProvider``
is the sole implementation of the upstream.  It lives behind
``FaultController`` which allows live flipping of fault scenarios.

The provider is **deterministic-by-design**: ``random.Random(seed)`` is
the reproducibility feature; ambient identity/clock do not apply to
seeded draws.  Identical seeds produce identical rate sequences.

Scenario behavior:

- ``HEALTHY`` — always answers with a fresh random-walk quote
- ``FLAKY`` — ~70% of calls raise ``UpstreamTimeoutError``
- ``DOWN`` — hard failure on every call (``UpstreamUnavailableError``)
- ``SLOW`` — adds 50ms latency to every call
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from enum import Enum
import random

from lexigram.primitives import clock
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
    """Upstream health scenarios driven by the FaultController.

    Each scenario produces a different failure mode in the simulated
    upstream, allowing the resilience pipeline to be exercised live.
    """

    HEALTHY = "healthy"
    FLAKY = "flaky"
    DOWN = "down"
    SLOW = "slow"


class FaultController:
    """Container-managed holder of the active upstream scenario.

    Registered as a singleton in ``RatesProvider.register()`` so the same
    instance is shared across the service and API controller layers.

    Attributes:
        current: The active scenario (read-only property).
    """

    def __init__(self, initial: Scenario = Scenario.HEALTHY) -> None:
        self._scenario = initial

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
        # deterministic-by-design: stdlib Random(seed) IS the reproducibility
        # feature; ambient identity/clock do not apply to seeded draws.
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
        if (
            scenario is Scenario.FLAKY
            and self._rng.random() < _FLAKY_TIMEOUT_PROBABILITY
        ):
            raise UpstreamTimeoutError(f"upstream timed out for {pair}")
        if scenario is Scenario.SLOW:
            await asyncio.sleep(_SLOW_DELAY_SECONDS)
        drift = Decimal(str(self._rng.uniform(-0.005, 0.005)))
        rate = (Decimal(_BASE_RATES[pair]) * (Decimal("1") + drift)).quantize(
            Decimal("0.00001")
        )
        return RateQuote(
            pair=pair, rate=rate, fetched_at=clock.now().timestamp(), source="upstream"
        )


__all__ = ["FaultController", "Scenario", "SimulatedRatesProvider"]
