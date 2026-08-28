"""Lifecycle wiring for the Artifact Vault showcase."""

from __future__ import annotations

from typing import TYPE_CHECKING

from artifact_vault.config import ArtifactVaultConfig
from artifact_vault.controllers.api import ArtifactVaultApiController
from artifact_vault.services.vault import ArtifactVaultService
from lexigram.contracts import BlobStoreProtocol
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


class ArtifactVaultProvider(Provider):
    """Resolve the package-owned blob store and seed one browser artifact."""

    name = "artifact_vault"
    config_key: str | None = "artifact_vault"
    config_model: type | None = ArtifactVaultConfig

    def __init__(self) -> None:
        super().__init__()
        self._service: ArtifactVaultService | None = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        cfg = self.config or ArtifactVaultConfig()
        container.singleton(ArtifactVaultConfig, instance=cfg)
        container.singleton(ArtifactVaultApiController, ArtifactVaultApiController)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        store = await container.resolve(BlobStoreProtocol)
        config = await container.resolve(ArtifactVaultConfig)
        service = ArtifactVaultService(store, config)
        await service.seed()
        self._service = service
        container.bind(
            ArtifactVaultApiController, ArtifactVaultApiController(service=service)
        )

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        if self._service is None:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                category=HealthCheckCategory.READINESS,
            )
        health = await self._service.health()
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus(health["status"]),
            category=HealthCheckCategory.READINESS,
            details=health["details"],
        )


__all__ = ["ArtifactVaultProvider"]
