"""Admin tenancy sub-provider — wires multi-tenancy into the admin panel."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.admin.multitenancy.adapter import TenantProviderRegistry
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.admin.config import AdminConfig
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

logger = get_logger(__name__)


class AdminTenancySubProvider:
    """Manages tenant resolution, registry, and data source scoping."""

    def __init__(self, config: AdminConfig) -> None:
        self._config = config

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register tenant registry and middleware in the DI container."""
        if not self._config.tenancy.enabled:
            logger.debug("admin.tenancy_disabled")
            return

        registry = TenantProviderRegistry()
        container.singleton(TenantProviderRegistry, registry)
        logger.debug("admin.tenancy_registered")

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Tenancy boot — no additional init required."""

    async def shutdown(self) -> None:
        """Tenancy shutdown."""

    def get_middleware(self) -> tuple[type, dict[str, Any]] | None:
        """Return the tenant middleware tuple if tenancy is enabled.

        Returns (AdminTenantMiddleware, {config}) or None.
        """
        if not self._config.tenancy.enabled:
            return None
        from lexigram.admin.middleware.tenant import AdminTenantMiddleware

        return (AdminTenantMiddleware, {"config": self._config.tenancy})

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report tenancy sub-provider health."""
        return HealthCheckResult(
            component="admin.tenancy",
            status=HealthStatus.HEALTHY,
            details={
                "enabled": self._config.tenancy.enabled,
            },
        )
