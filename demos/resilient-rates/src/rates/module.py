"""Module for the resilient rates demo."""

from __future__ import annotations

from lexigram.cache.config import CacheBackendConfig, CacheConfig
from lexigram.cache.module import CacheModule
from lexigram.cache.types import BackendType
from lexigram.di.module import DynamicModule, Module, module
from lexigram.resilience.module import ResilienceModule
from rates.di.provider import RatesProvider
from rates.provider import FaultController, SimulatedRatesProvider
from rates.service import RatesService


def _memory_cache_config() -> CacheConfig:
    """Return an offline memory-backend cache configuration."""
    return CacheConfig(
        backends=[
            CacheBackendConfig(
                name="default",
                type=BackendType.MEMORY,
                default=True,
            )
        ]
    )


@module()
class RatesModule(Module):
    """Root module: resilience + cache + rate desk services."""

    @classmethod
    def configure(cls) -> DynamicModule:
        return DynamicModule(
            module=cls,
            imports=[
                ResilienceModule.configure(),
                CacheModule.configure(_memory_cache_config()),
            ],
            providers=[RatesProvider],
            exports=[FaultController, SimulatedRatesProvider, RatesService],
        )


__all__ = ["RatesModule"]
