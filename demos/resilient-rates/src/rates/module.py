"""Module for the resilient rates demo.

Blueprint reference example (Wave 0 Task A): configuration is bound from
``application.yaml`` via :func:`rates.config.bind_application` — this file
contains no literal host/port/security values. See ``rates.config`` for why
binding is explicit rather than relying on provider auto-injection.
"""

from __future__ import annotations

from dataclasses import replace

from lexigram.cache.module import CacheModule
from lexigram.di.module import DynamicModule, Module, module
from lexigram.resilience.module import ResilienceModule
from lexigram.web import WebModule
from rates.config import bind_application
from rates.controllers.api import RatesApiController
from rates.di.provider import RatesProvider
from rates.repository.simulated_upstream import FaultController, SimulatedRatesProvider
from rates.services.rates_service import RatesService
from rates.ui.pages import RatesPageController


@module()
class RatesModule(Module):
    """Root module: resilience + cache + rate desk services."""

    @classmethod
    def configure(cls, port: int | None = None) -> DynamicModule:
        web_config, cache_config, demo_config = bind_application()
        if port is not None:  # embedded-hub override; children never serve
            web_config = replace(
                web_config, server=replace(web_config.server, port=port)
            )
        return DynamicModule(
            module=cls,
            imports=[
                ResilienceModule.configure(),
                CacheModule.configure(cache_config),
                WebModule.configure(
                    controllers=[RatesApiController, RatesPageController],
                    web_config=web_config,
                ),
            ],
            providers=[RatesProvider(config=demo_config)],
            exports=[FaultController, SimulatedRatesProvider, RatesService],
        )


__all__ = ["RatesModule"]
