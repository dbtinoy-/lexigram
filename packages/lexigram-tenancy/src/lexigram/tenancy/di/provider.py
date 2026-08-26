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
                When ``None``, the orchestrator injects the typed ``tenancy``
                yaml section after construction (``config_key``) and before
                :meth:`register`; framework defaults apply if no section exists.
        """
        from lexigram.contracts.core.provider import ProviderPriority

        super().__init__()
        self.priority = ProviderPriority.INFRASTRUCTURE
        self._requested_config = config
        # Keep ``None`` when constructed without a config so the orchestrator
        # can late-inject the yaml section into provider.config. Sub-provider
        # composition is deferred to register() in that case.
        self._config = config
        self._sub_providers: list[Provider] = []
        if config is not None:
            self._compose_sub_providers(config)

    def _compose_sub_providers(self, cfg: TenancyConfig) -> None:
        """(Re)build sub-providers from *cfg*.

        Called from ``__init__`` when an explicit config was supplied and
        again from ``register()`` when the orchestrator injected the yaml
        section after construction. Recomposition before any ``register()``
        call is safe — nothing has been registered yet.

        Args:
            cfg: The effective configuration driving sub-provider wiring.
        """
        self._config = cfg
        self._sub_providers = [
            TenantResolutionProvider(cfg.resolution),
            TenantLifecycleProvider(cfg.lifecycle),
            TenantConfigProvider(cfg.overrides),
            TenantMigrationProvider(),
            TenantIntegrationProvider(cfg.integration),
        ]

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Delegate registration to all sub-providers.

        Late config binding: when ``configure()`` ran with no explicit config,
        the orchestrator injects the typed ``tenancy`` yaml section after
        construction and before this call; sub-providers are composed now so
        the automatic path behaves identically to the explicit one. An
        explicit constructor config always wins over any later assignment to
        :attr:`config`.

        Args:
            container: The DI container registrar.
        """
        if self._requested_config is not None:
            if not self._sub_providers:
                self._compose_sub_providers(self._requested_config)
            else:
                self._config = self._requested_config
        else:
            injected = (
                self.config
                if isinstance(getattr(self, "config", None), TenancyConfig)
                else None
            )
            self._compose_sub_providers(injected or TenancyConfig())
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
