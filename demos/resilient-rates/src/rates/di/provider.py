"""Provider wiring for the resilient rates demo."""

from __future__ import annotations

from lexigram.contracts.core.di import (
    ContainerRegistrarProtocol,
    ContainerResolverProtocol,
)
from lexigram.contracts.infra.cache.protocols import CacheBackendProtocol
from lexigram.contracts.infra.resilience.protocols import (
    ResiliencePipelineFactoryProtocol,
)
from lexigram.di.provider import Provider
from rates.api import RatesApiController
from rates.provider import FaultController, SimulatedRatesProvider
from rates.service import RatesService


class RatesProvider(Provider):
    """Register the rate desk services as container-managed singletons."""

    name = "rates"

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind singletons; RatesService builds lazily from booted deps."""
        faults = FaultController()
        container.singleton(FaultController, instance=faults)
        container.singleton(
            SimulatedRatesProvider,
            instance=SimulatedRatesProvider(faults=faults),
        )
        # Cache backend and resilience pipeline are wired by the imported
        # modules' own providers; the lazy factory below resolves them at
        # first use — after every provider has booted.
        container.singleton(RatesService, factory=self._build_service)
        container.singleton(RatesApiController, factory=self._build_controller)

    async def _build_service(self, resolver: ContainerResolverProtocol) -> RatesService:
        """Assemble ``RatesService`` from its booted collaborators."""
        return RatesService(
            cache=await resolver.resolve(CacheBackendProtocol),
            pipeline_factory=await resolver.resolve(ResiliencePipelineFactoryProtocol),
            provider=await resolver.resolve(SimulatedRatesProvider),
            faults=await resolver.resolve(FaultController),
        )

    async def _build_controller(
        self, resolver: ContainerResolverProtocol
    ) -> RatesApiController:
        return RatesApiController(
            service=await resolver.resolve(RatesService),
            faults=await resolver.resolve(FaultController),
        )


__all__ = ["RatesProvider"]
