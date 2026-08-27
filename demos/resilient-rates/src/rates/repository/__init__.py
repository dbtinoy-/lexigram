"""Scripted upstream adapters for the resilient rates demo.

Convention followed: **Repository pattern** — ``SimulatedRatesProvider``
is the simulated upstream, behind a ``FaultController`` that allows
live flipping of fault scenarios.  The provider is deterministic-by-
design (seeded ``random.Random``), so identical seeds produce identical
draw sequences.

Exports:

- ``SimulatedRatesProvider`` — deterministic random-walk FX rates
- ``FaultController`` — container-managed holder of the active scenario
- ``Scenario`` — enum of upstream health states
"""

from __future__ import annotations

from rates.repository.simulated_upstream import (
    FaultController,
    Scenario,
    SimulatedRatesProvider,
)

__all__ = ["FaultController", "Scenario", "SimulatedRatesProvider"]
