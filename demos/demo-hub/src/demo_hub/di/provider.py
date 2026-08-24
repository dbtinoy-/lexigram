"""Provider wiring for the demo-hub demo."""

from __future__ import annotations

from demo_hub.controllers.api import HubApiController
from demo_hub.fleet import Fleet
from demo_hub.services.registry import ServiceRegistry
from lexigram.contracts.core.di import (
    ContainerRegistrarProtocol,
    ContainerResolverProtocol,
)
from lexigram.contracts.core.health import HealthCheckResult
from lexigram.di.provider import Provider


class HubProvider(Provider):
    """Register the hub services as container-managed singletons."""

    name = "demo_hub"

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report component readiness."""
        return HealthCheckResult(component=self.name)

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind singletons."""
        registry = ServiceRegistry()
        container.singleton(ServiceRegistry, instance=registry)
        container.singleton(Fleet, instance=Fleet(registry))
        container.singleton(HubApiController, factory=self._build_controller)

    async def _build_controller(
        self, resolver: ContainerResolverProtocol
    ) -> HubApiController:
        return HubApiController(
            fleet=await resolver.resolve(Fleet),
        )
