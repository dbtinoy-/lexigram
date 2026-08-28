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

    def __init__(
        self, config: FeatureFlagsConfig | dict[str, Any] | None = None
    ) -> None:
        """Create the feature-flags provider.

        Args:
            config: Optional feature-flag configuration.  When omitted,
                defaults are used (all flags disabled, cache TTL 60 s).  The
                value stays ``None`` until ``register()`` so the orchestrator
                can inject the yaml section (via ``config_key``) first.
        """
        super().__init__()
        self._config: FeatureFlagsConfig | dict[str, Any] | None = config
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

        Late config binding: when ``configure()`` ran with no explicit config,
        the orchestrator has injected the yaml section into ``self.config``
        before this call; only fall back to defaults if it did not.
        """
        cfg = self._config
        if isinstance(cfg, dict):
            cfg = FeatureFlagsConfig(**cfg)
        if cfg is None:
            cfg = FeatureFlagsConfig()
        self._config = cfg

        container.singleton(FeatureFlagsConfig, cfg)

        if not cfg.enabled:
            logger.info("features_disabled", reason="FeatureFlagsConfig.enabled=False")
            return

        # Normalize both the legacy boolean seed format and rich definitions
        # supplied by application configuration. One normalized set of flags
        # powers both the simple protocol and the rich manager API.
        initial = {
            flag_name: self._coerce_flag(flag_name, definition)
            for flag_name, definition in cfg.initial_flags.items()
        }

        # Simple boolean provider for the FlagProviderProtocol contract.
        simple = LocalProvider()
        for flag_name, flag in initial.items():
            simple.set_flag_sync(flag_name, flag.enabled)
        container.singleton(FlagProviderProtocol, simple)
        self._simple_provider = simple

        # Rich provider + manager for full evaluation API.
        local = LocalProvider(initial)
        manager = FlagManager(
            local,
            cache_ttl=cfg.cache_ttl,
            default_enabled=cfg.default_enabled,
        )
        container.singleton(FlagManager, manager)
        from lexigram.contracts.feature_flags.protocols import FlagManagerProtocol

        container.singleton(FlagManagerProtocol, manager)
        self._manager = manager

    @staticmethod
    def _coerce_flag(name: str, definition: object) -> Flag:
        """Normalize one configured seed into a rich :class:`Flag`.

        ``initial_flags`` historically accepted ``name -> bool`` mappings.
        Keeping that shape while accepting ``Flag`` instances and YAML-friendly
        mappings lets applications opt into percentage, attribute, and variant
        evaluation without replacing the provider after boot.
        """
        if isinstance(definition, Flag):
            if definition.name != name:
                raise ValueError(
                    f"Flag definition key {name!r} does not match name "
                    f"{definition.name!r}"
                )
            return definition

        if isinstance(definition, bool):
            return Flag(name=name, type=FlagType.BOOLEAN, enabled=definition)

        if isinstance(definition, dict):
            payload = dict(definition)
            payload["name"] = name
            flag_type = payload.get("type", FlagType.BOOLEAN)
            if not isinstance(flag_type, FlagType):
                flag_type = FlagType(flag_type)
            payload["type"] = flag_type
            return Flag(**payload)

        raise TypeError(
            f"initial_flags[{name!r}] must be bool, Flag, or a flag-definition mapping; "
            f"got {type(definition).__name__}"
        )

    async def boot(self, container: BootContainerProtocol) -> None:
        """Wire the event bus into the flag manager when one is available."""
        if self._manager is None:
            return

        from lexigram.contracts.events.protocols import EventBusProtocol

        # EventBusProtocol is optional. Use the container's explicit optional
        # resolution path so unrelated wiring failures are not silently hidden.
        event_bus = await container.resolve_optional(EventBusProtocol)
        if event_bus is not None:
            self._manager._event_bus = event_bus

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
            len(self._config.initial_flags)
            if isinstance(self._config, FeatureFlagsConfig)
            and self._config.initial_flags
            else 0
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
