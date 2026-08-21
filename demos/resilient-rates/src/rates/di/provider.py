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
from rates.provider import FaultController, SimulatedRatesProvider
from rates.service import RatesService


class RatesProvider(Provider):
    """Register the rate desk services as container-managed singletons."""

    name = "rates"

    def __init__(self) -> None:
        super().__init__()
        self._service: RatesService | None = None

    def _get_service(self) -> RatesService:
        """Return the service assembled during boot."""
        if self._service is None:
            raise RuntimeError("RatesProvider has not been booted yet")
        return self._service

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind singletons; collaborators resolve only in boot()."""
        faults = FaultController()
        container.singleton(FaultController, instance=faults)
        container.singleton(
            SimulatedRatesProvider,
            instance=SimulatedRatesProvider(faults=faults),
        )
        # RatesService depends on the cache backend and pipeline factory,
        # which are wired by the imported modules' own providers; bind a
        # lazy factory now and assemble in boot().
        container.singleton(RatesService, factory=self._get_service)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Assemble RatesService from booted collaborators."""
        faults = await container.resolve(FaultController)
        provider = await container.resolve(SimulatedRatesProvider)
        cache = await container.resolve(CacheBackendProtocol)
        pipeline_factory = await container.resolve(ResiliencePipelineFactoryProtocol)

        self._service = RatesService(
            cache=cache,
            pipeline_factory=pipeline_factory,
            provider=provider,
            faults=faults,
        )


__all__ = ["RatesProvider"]
