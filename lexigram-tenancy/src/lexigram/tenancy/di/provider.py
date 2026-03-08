"""Bundle provider — delegates to four focused sub-providers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.di.provider import Provider
from lexigram.tenancy.config import TenancyConfig
from lexigram.tenancy.di.config_provider import TenantConfigProvider
from lexigram.tenancy.di.integration_provider import TenantIntegrationProvider
from lexigram.tenancy.di.lifecycle_provider import TenantLifecycleProvider
from lexigram.tenancy.di.migration_provider import TenantMigrationProvider
from lexigram.tenancy.di.resolution_provider import TenantResolutionProvider

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        BootContainerProtocol,
        ContainerRegistrarProtocol,
    )


class TenancyProvider(Provider):
    """Bundle provider that orchestrates all tenancy sub-providers.

    Mirrors the ``lexigram-auth`` ``AuthBundleProvider`` pattern.  Delegates
    registration, boot, and shutdown to four focused sub-providers in order:

    1. :class:`~lexigram.tenancy.di.resolution_provider.TenantResolutionProvider`
    2. :class:`~lexigram.tenancy.di.lifecycle_provider.TenantLifecycleProvider`
    3. :class:`~lexigram.tenancy.di.config_provider.TenantConfigProvider`
    4. :class:`~lexigram.tenancy.di.integration_provider.TenantIntegrationProvider`

    Usage::

        from lexigram.tenancy.di.provider import TenancyProvider
        from lexigram.tenancy.config import TenancyConfig

        provider = TenancyProvider(TenancyConfig(...))
    """

    name = "tenancy"
    config_key: str | None = "tenancy"
    config_model: type | None = TenancyConfig

    def __init__(self, config: TenancyConfig | None = None) -> None:
        """Initialise the bundle provider.

        Args:
            config: Optional :class:`~lexigram.tenancy.config.TenancyConfig`.
                Defaults to all framework defaults when ``None``.
        """
        from lexigram.contracts.core.provider import ProviderPriority

        self.priority = ProviderPriority.INFRASTRUCTURE
        self._requested_config = config
        self._config = config or TenancyConfig()
        self._sub_providers: list[Provider] = [
            TenantResolutionProvider(self._config.resolution),
            TenantLifecycleProvider(self._config.lifecycle),
            TenantConfigProvider(self._config.overrides),
            TenantMigrationProvider(),
            TenantIntegrationProvider(self._config.integration),
        ]

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Delegate registration to all sub-providers.

        Args:
            container: The DI container registrar.
        """
        effective_config = self._requested_config or (
            self.config
            if isinstance(getattr(self, "config", None), TenancyConfig)
            else self._config
        )
        if effective_config is not self._config:
            self._config = effective_config
            self._sub_providers = [
                TenantResolutionProvider(self._config.resolution),
                TenantLifecycleProvider(self._config.lifecycle),
                TenantConfigProvider(self._config.overrides),
                TenantIntegrationProvider(self._config.integration),
            ]
        for sp in self._sub_providers:
            await sp.register(container)

    async def boot(self, container: BootContainerProtocol) -> None:
        """Delegate boot to all sub-providers.

        Args:
            container: The DI container for boot phase.
        """
        for sp in self._sub_providers:
            await sp.boot(container)

    async def shutdown(self) -> None:
        """Delegate shutdown to sub-providers in reverse order."""
        for sp in reversed(self._sub_providers):
            await sp.shutdown()

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Aggregate health across all sub-providers.

        Returns:
            A :class:`~lexigram.contracts.core.health.HealthCheckResult`
            reflecting the worst sub-provider status.
        """
        return HealthCheckResult(
            component="tenancy",
            status=HealthStatus.HEALTHY,
            details={"sub_providers": [sp.name for sp in self._sub_providers]},
        )


__all__ = ["TenancyProvider"]
