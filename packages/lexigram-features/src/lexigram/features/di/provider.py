"""DI provider for the feature-flag subsystem.

:class:`FeatureFlagsProvider` registers a :class:`~lexigram.features.manager.FlagManager`
singleton in the container so application services can resolve it via DI
rather than constructing it manually.

The default configuration uses a
:class:`~lexigram.features.backends.local.LocalProvider` for
the simple boolean contract and a
:class:`~lexigram.features.backends.local.LocalProvider` backed by
``config.initial_flags`` for the rich evaluation API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from lexigram.contracts.core import ProviderPriority
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.feature_flags import FlagProviderProtocol
from lexigram.di.provider import Provider
from lexigram.features.backends.local import LocalProvider
from lexigram.features.config import FeatureFlagsConfig
from lexigram.features.manager import FlagManager
from lexigram.features.types import Flag, FlagType
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        BootContainerProtocol,
        ContainerRegistrarProtocol,
    )


logger = get_logger(__name__)


class FeatureFlagsProvider(Provider):
    """Provider that registers feature-flag infrastructure in the container.

    Registers:

    * ``FlagProviderProtocol`` (simple boolean contract) as a singleton backed by
      :class:`~lexigram.features.backends.local.LocalProvider`.
    * ``FlagManager`` as a singleton wrapping a
      :class:`~lexigram.features.backends.local.LocalProvider` seeded from
      :attr:`~lexigram.features.config.FeatureFlagsConfig.initial_flags`.
    """

    name = "features"
    config_key: str | None = "features"
    config_model: type | None = FeatureFlagsConfig
    priority = ProviderPriority.INFRASTRUCTURE

    def __init__(self, config: FeatureFlagsConfig | None = None) -> None:
        """Create the feature-flags provider.

        Args:
            config: Optional feature-flag configuration.  When omitted,
                defaults are used (all flags disabled, cache TTL 60 s).
        """
        super().__init__()
        self._config = config or FeatureFlagsConfig()
        self._simple_provider: LocalProvider | None = None
        self._manager: FlagManager | None = None

    @classmethod
    def from_config(cls, config: FeatureFlagsConfig, **context: Any) -> Self:
        """Create provider from config object."""
        return cls(config=config)

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register flag infrastructure in the container.

        Registers ``FlagProviderProtocol`` (simple boolean API) and ``FlagManager``
        (rich evaluation API) as singletons, seeded from the provider config.
        """
        container.singleton(FeatureFlagsConfig, self._config)

        if not self._config.enabled:
            logger.info("features_disabled", reason="FeatureFlagsConfig.enabled=False")
            return

        # Simple boolean provider for the FlagProviderProtocol contract.
        simple = LocalProvider()
        for flag_name, enabled in self._config.initial_flags.items():
            simple.set_flag_sync(flag_name, enabled)
        container.singleton(FlagProviderProtocol, simple)
        self._simple_provider = simple

        # Rich provider + manager for full evaluation API.
        initial: dict[str, Flag] = {
            flag_name: Flag(name=flag_name, type=FlagType.BOOLEAN, enabled=enabled)
            for flag_name, enabled in self._config.initial_flags.items()
        }
        local = LocalProvider(initial)
        manager = FlagManager(
            local,
            cache_ttl=self._config.cache_ttl,
            default_enabled=self._config.default_enabled,
        )
        container.singleton(FlagManager, manager)
        from lexigram.contracts.feature_flags.protocols import FlagManagerProtocol

        container.singleton(FlagManagerProtocol, manager)
        self._manager = manager

    async def boot(self, container: BootContainerProtocol) -> None:
        """Wire the event bus into the flag manager when one is available."""
        if self._manager is None:
            return
        try:
            from lexigram.contracts.events.protocols import EventBusProtocol

            event_bus = await container.resolve(EventBusProtocol)
            self._manager._event_bus = event_bus
        except Exception as e:  # noqa: BLE001
            logger.debug(
                "event_bus_unavailable",
                error=str(e),
            )  # EventBusProtocol is optional; feature flags work without it

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check health of feature flags.

        Feature flags are in-memory and have no external dependencies,
        so this always returns HEALTHY.

        Args:
            timeout: Not used - feature flags have no external dependencies.

        Returns:
            HealthCheckResult showing healthy status.
        """
        flag_count = (
            len(self._config.initial_flags) if self._config.initial_flags else 0
        )
        return HealthCheckResult(
            component="features",
            status=HealthStatus.HEALTHY,
            message=f"Feature flags operational with {flag_count} initial flags",
            details={"initial_flags": flag_count},
        )

    async def shutdown(self) -> None:
        """No resources to release for the feature-flags module."""

    def get_simple_provider(self) -> LocalProvider | None:
        """Return the registered simple provider after registration.

        Returns:
            The ``LocalProvider`` instance, or ``None`` before registration.
        """
        return self._simple_provider

    def get_manager(self) -> FlagManager | None:
        """Return the registered manager after registration.

        Returns:
            The ``FlagManager`` instance, or ``None`` before registration.
        """
        return self._manager


__all__ = ["FeatureFlagsProvider"]
