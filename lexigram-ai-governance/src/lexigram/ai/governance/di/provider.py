"""Governance DI provider."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from lexigram.ai.governance.config import GovernanceConfig
from lexigram.ai.governance.relay_billing.di import (
    boot_relay_billing,
    register_relay_billing,
)
from lexigram.ai.governance.services.manager import AIGovernanceManager
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.di.provider import Provider
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        BootContainerProtocol,
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

logger = get_logger(__name__)


class GovernanceProvider(Provider):
    """Provider for AI Governance.

    Registers :class:`~lexigram.ai.governance.services.manager.AIGovernanceManager`.
    """

    name = "governance"
    priority = ProviderPriority.DOMAIN
    config_key: str | None = "ai_governance"
    config_model: type | None = GovernanceConfig

    def __init__(
        self,
        config: GovernanceConfig | dict | None = None,
    ) -> None:
        super().__init__()
        if isinstance(config, dict):
            config = GovernanceConfig(**config)
        elif config is not None and not isinstance(config, GovernanceConfig):
            raise TypeError(
                f"config must be GovernanceConfig or dict, got {type(config).__name__}"
            )
        self._requested_config = config
        self._config = config or GovernanceConfig()

    @classmethod
    def from_config(
        cls,
        config: GovernanceConfig,
        **context: object,
    ) -> GovernanceProvider:
        """Factory method for DI container setup."""
        del context
        return cls(config)

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register the governance services."""
        from lexigram.contracts.ai.governance import AIGovernanceProtocol

        self._config = self._requested_config or (
            self.config
            if isinstance(getattr(self, "config", None), GovernanceConfig)
            else self._config
        )
        container.singleton(GovernanceConfig, self._config)
        register_relay_billing(container, self._config)

        if not self._config.enabled:
            logger.info("governance_disabled", reason="GovernanceConfig.enabled=False")
            return

        manager = AIGovernanceManager(self._config)
        container.singleton(AIGovernanceManager, manager)
        container.singleton(AIGovernanceProtocol, manager)

        # Register resource unit registry + tracker when units are configured.
        # Reuse the manager's internal tracker so consume/release routes the
        # same backend regardless of which protocol is resolved.
        if self._config.resource_units and manager.resource_tracker is not None:
            from lexigram.ai.governance.resource.registry import (
                ResourceUnitRegistry,
            )
            from lexigram.ai.governance.resource.tracker import (
                ResourceUnitTracker,
            )

            assert manager._resource_registry is not None  # noqa: S101
            container.singleton(ResourceUnitRegistry, manager._resource_registry)
            container.singleton(ResourceUnitTracker, manager.resource_tracker)
            logger.info(
                "resource_units_registered",
                count=len(self._config.resource_units),
            )

        logger.info("governance_registered")

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Boot phase."""
        await boot_relay_billing(
            cast("BootContainerProtocol", container),
            self._config,
        )
        logger.debug("governance_booted")

    async def shutdown(self) -> None:
        """Shutdown phase."""
        logger.debug("governance_shutdown")

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Health check — always healthy (in-process domain provider).

        No external backend to ping.

        Args:
            timeout: Ignored for in-process providers.

        Returns:
            Always HEALTHY — no external backend to ping.
        """
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            details={"status": "operational"},
        )


__all__ = ["GovernanceProvider"]
