"""Forex rate desk demo — resilience and cache teaching artifacts."""

from __future__ import annotations

from rates.module import RatesModule
from rates.provider import FaultController, SimulatedRatesProvider
from rates.services.rates_service import RatesService

__all__ = [
    "FaultController",
    "RatesModule",
    "RatesService",
    "SimulatedRatesProvider",
]
