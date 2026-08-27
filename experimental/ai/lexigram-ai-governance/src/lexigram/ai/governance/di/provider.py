"""Governance DI provider."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from lexigram.ai.governance.config import GovernanceConfig
from lexigram.ai.governance.relay_billing.di import (
    boot_relay_billing,
    register_relay_billing,
)
from lexigram.ai.governance.relay_channels.di import (
    boot_relay_channels,
    register_relay_channels,
)
from lexigram.ai.governance.relay_ledger.di import (
    boot_relay_ledger,
    register_relay_ledger,
)
from lexigram.ai.governance.relay_logs.di import (
    boot_relay_logs,
    register_relay_logs,
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
        self._config = config if config is not None else GovernanceConfig()

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
        register_relay_logs(container, self._config)
        register_relay_channels(container, self._config)
        register_relay_ledger(container, self._config)

        if not self._config.enabled:
            logger.info("governance_disabled", reason="GovernanceConfig.enabled=False")
            return

        from lexigram.ai.governance.audit import AIAuditStore, InMemoryAuditStore

        audit_store: AIAuditStore = InMemoryAuditStore()
        container.singleton(AIAuditStore, audit_store)

        manager = AIGovernanceManager(self._config, audit_store=audit_store)
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
        """Attach governance persistence and boot remaining sub-systems.

        The persistence backend is resolved here, after container freezing,
        so that the optional database/cache backends are available and the
        persistence-aware manager can be rebound (spec: DI ordering).

        Args:
            container: The DI container.
        """
        if not self._config.enabled:
            return

        from lexigram.ai.governance.audit import AIAuditStore
        from lexigram.contracts import CacheBackendProtocol, DatabaseProviderProtocol
        from lexigram.contracts.ai.governance import AIGovernanceProtocol

        manager = await container.resolve(AIGovernanceManager)
        audit_store = await container.resolve_optional(AIAuditStore)

        database = await container.resolve_optional(DatabaseProviderProtocol)
        cache = await container.resolve_optional(CacheBackendProtocol)

        if database is not None:
            from lexigram.ai.governance.persistence import (
                DatabaseGovernancePersistence,
                GovernancePersistence,
            )

            persistence = cast(
                "GovernancePersistence", DatabaseGovernancePersistence(database)
            )
            manager_with_persistence = AIGovernanceManager(
                self._config, persistence=persistence, audit_store=audit_store
            )
        elif cache is not None:
            from lexigram.ai.governance.persistence import (
                GovernancePersistence,
                RedisGovernancePersistence,
            )

            persistence = cast(
                "GovernancePersistence", RedisGovernancePersistence(cache)
            )
            manager_with_persistence = AIGovernanceManager(
                self._config, persistence=persistence, audit_store=audit_store
            )
        else:
            logger.info(
                "governance_persistence_skip",
                reason="no database or cache backend available",
                backend="in-memory",
            )
            manager_with_persistence = manager

        if manager_with_persistence is not manager:
            boot_container = cast("BootContainerProtocol", container)
            boot_container.bind(AIGovernanceManager, manager_with_persistence)
            boot_container.bind(AIGovernanceProtocol, manager_with_persistence)

            # Keep the resource-unit tracker/registry routing through the
            # same backend as the rebound manager (see register()).
            if (
                self._config.resource_units
                and manager_with_persistence.resource_tracker is not None
            ):
                from lexigram.ai.governance.resource.registry import (
                    ResourceUnitRegistry,
                )
                from lexigram.ai.governance.resource.tracker import (
                    ResourceUnitTracker,
                )

                boot_container.bind(
                    ResourceUnitRegistry, manager_with_persistence._resource_registry
                )
                boot_container.bind(
                    ResourceUnitTracker, manager_with_persistence.resource_tracker
                )

        await boot_relay_billing(
            cast("BootContainerProtocol", container),
            self._config,
        )
        await boot_relay_logs(
            cast("BootContainerProtocol", container),
            self._config,
        )
        await boot_relay_channels(
            cast("BootContainerProtocol", container),
            self._config,
        )
        await boot_relay_ledger(
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
