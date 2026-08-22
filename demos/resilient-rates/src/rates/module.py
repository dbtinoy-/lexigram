"""Module for the resilient rates demo."""

from __future__ import annotations

import os

from lexigram.cache.config import CacheBackendConfig, CacheConfig
from lexigram.cache.module import CacheModule
from lexigram.cache.types import BackendType
from lexigram.di.module import DynamicModule, Module, module
from lexigram.resilience.module import ResilienceModule
from lexigram.web import WebConfig, WebModule
from lexigram.web.config import ServerConfig
from lexigram.web.security import SecurityConfig
from rates.api import RatesApiController
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
    def configure(cls, port: int | None = None) -> DynamicModule:
        selected_port = (
            port if port is not None else int(os.environ.get("RATES_PORT", "7073"))
        )
        return DynamicModule(
            module=cls,
            imports=[
                ResilienceModule.configure(),
                CacheModule.configure(_memory_cache_config()),
                WebModule.configure(
                    controllers=[RatesApiController],
                    web_config=WebConfig(
                        server=ServerConfig(
                            host="127.0.0.1",
                            port=selected_port,
                        ),
                        # Scenario flips come from curl/external tools,
                        # not a browser form — disable CSRF.
                        security=SecurityConfig(enable_csrf=False),
                    ),
                ),
            ],
            providers=[RatesProvider],
            exports=[FaultController, SimulatedRatesProvider, RatesService],
        )


__all__ = ["RatesModule"]
