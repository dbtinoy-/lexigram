"""Forex rate desk demo — resilience and cache teaching artifacts."""

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
