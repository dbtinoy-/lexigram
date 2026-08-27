"""Forex rate desk demo — resilience and cache teaching artifacts.

Convention followed: **Package exports** — ``__init__.py`` re-exports
the public API surface without defining logic.

Exports:

- ``create_app`` — composition root for the application
- ``RatesService`` — cache-aside + resilience pipeline service
- ``FaultController`` — scenario flipper (container-managed singleton)
- ``SimulatedRatesProvider`` — deterministic upstream with scriptable faults
"""

from __future__ import annotations

from rates.app import create_app
from rates.repository.simulated_upstream import FaultController, SimulatedRatesProvider
from rates.services.rates_service import RatesService

__all__ = [
    "FaultController",
    "RatesService",
    "SimulatedRatesProvider",
    "create_app",
]
