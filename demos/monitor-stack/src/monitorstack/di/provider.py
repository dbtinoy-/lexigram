"""Lifecycle wiring for the browser-visible observability demo."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.core.health import (
    HealthCheckCategory,
    HealthCheckResult,
    HealthStatus,
)
from lexigram.contracts.observability.metrics import MetricsCollectorProtocol
from lexigram.contracts.observability.tracing import TracerProtocol
from lexigram.di.provider import Provider
from lexigram.monitor.health import HealthCheckRegistry
from monitorstack.config import MonitorStackConfig
from monitorstack.controllers.api import MonitorApiController

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

__all__ = ["MonitorStackProvider"]


class MonitorStackProvider(Provider):
    """Bind one self-check and the monitor protocols to the UI controller.

    ``MonitorModule`` owns metric instruments, in-memory tracing, and the
    categorised health registry. The demo owns no replacement observability
    implementation; it only exposes a small operational console.
    """

    name = "monitorstack"
    config_key: str | None = "monitorstack"
    config_model: type | None = MonitorStackConfig

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Declare config and controller bindings."""
        cfg = self.config or MonitorStackConfig()
        container.singleton(MonitorStackConfig, instance=cfg)
        container.singleton(MonitorApiController, MonitorApiController)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Resolve Lexigram monitor capabilities and register the self-check."""
        cfg = await container.resolve(MonitorStackConfig)
        metrics = await container.resolve(MetricsCollectorProtocol)
        tracer = await container.resolve(TracerProtocol)
        health_registry = await container.resolve(HealthCheckRegistry)

        async def self_check() -> HealthCheckResult:
            """Return a liveness/readiness signal for this demo process."""
            return HealthCheckResult(
                component="self",
                status=HealthStatus.HEALTHY,
                message=f"{cfg.service_name} is running",
            )

        health_registry.add(
            "self",
            self_check,
            category=HealthCheckCategory.READINESS,
        )

        container.bind(
            MonitorApiController,
            MonitorApiController(
                health_registry=health_registry,
                tracer=tracer,
                metrics=metrics,
                service_name=cfg.service_name,
            ),
        )

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report readiness of the monitor console."""
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            category=HealthCheckCategory.READINESS,
        )
