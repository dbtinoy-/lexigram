"""Provider wiring for the demo-hub demo.

Canonical shape: ``register()`` declares bindings (the fleet factory closes
over the registry it needs); ``boot()`` resolves the fleet and rebinds the
controller instance via ``container.bind()`` — controllers are otherwise
constructed by the router from the container.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from demo_hub.controllers.api import HubApiController
from demo_hub.fleet import Fleet
from demo_hub.services.registry import ServiceRegistry
from lexigram.contracts.core.health import (
    HealthCheckCategory,
    HealthCheckResult,
    HealthStatus,
)
from lexigram.di.provider import Provider

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

__all__ = ["HubProvider"]


class HubProvider(Provider):
    """Bind the hub services as container-managed singletons."""

    name = "demo_hub"

    _fleet: Fleet | None = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Declare bindings; the fleet is resolved in :meth:`boot`."""
        registry = ServiceRegistry()
        container.singleton(ServiceRegistry, instance=registry)
        container.singleton(Fleet, factory=lambda: Fleet(registry))
        container.singleton(HubApiController, HubApiController)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Resolve the fleet and rebind the controller with it attached."""
        self._fleet = await container.resolve(Fleet)
        container.bind(HubApiController, HubApiController(fleet=self._fleet))

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report fleet readiness (mounted vs failed children)."""
        fleet = self._fleet
        details = (
            {"mounted": len(fleet.mounted), "failures": len(fleet.failures)}
            if fleet is not None
            else {"mounted": 0, "failures": 0}
        )
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            category=HealthCheckCategory.READINESS,
            details=details,
        )
