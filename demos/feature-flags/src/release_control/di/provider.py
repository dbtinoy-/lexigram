"""Lifecycle wiring for the feature-flags showcase."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.core.health import (
    HealthCheckCategory,
    HealthCheckResult,
    HealthStatus,
)
from lexigram.di.provider import Provider
from lexigram.features.config import FeatureFlagsConfig
from lexigram.features.manager import FlagManager
from release_control.config import ReleaseControlConfig
from release_control.controllers.api import ReleaseControlApiController
from release_control.services.control import ReleaseControlService

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )


class ReleaseControlProvider(Provider):
    """Resolve Lexigram's FlagManager, then bind the browser-facing service."""

    name = "release_control"
    config_key: str | None = "release_control"
    config_model: type | None = ReleaseControlConfig

    def __init__(self) -> None:
        super().__init__()
        self._service: ReleaseControlService | None = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind the release-control config and API controller to the container."""
        cfg = self.config or ReleaseControlConfig()
        container.singleton(ReleaseControlConfig, instance=cfg)
        container.singleton(ReleaseControlApiController, ReleaseControlApiController)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Resolve the FlagManager and wire the release control service."""
        manager = await container.resolve(FlagManager)
        feature_config = await container.resolve(FeatureFlagsConfig)
        config = await container.resolve(ReleaseControlConfig)
        self._service = ReleaseControlService(manager, config, feature_config)
        container.bind(
            ReleaseControlApiController,
            ReleaseControlApiController(service=self._service),
        )

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Return readiness status based on whether the service has booted."""
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY if self._service else HealthStatus.UNHEALTHY,
            category=HealthCheckCategory.READINESS,
        )


__all__ = ["ReleaseControlProvider"]
