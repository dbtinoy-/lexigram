"""DI Provider for the config subsystem.

Loads application configuration and registers
:class:`~lexigram.config.main.LexigramConfig` as a singleton in the
DI container.

.. note::
    ``ConfigProvider`` performs file/env I/O in ``register()`` deliberately.
    Config must be present before any other provider's ``register()`` or
    ``boot()`` may call ``container.resolve(LexigramConfig)``.
    This is a one-off exception — no other provider does I/O in ``register()``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.config.lib import (
    ConfigLoader,
    ConfigRegistry,
    EnvironmentConfigSource,
    FileConfigSource,
)
from lexigram.config.main import LexigramConfig
from lexigram.contracts.core.config import ConfigProtocol
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.di.provider import Provider, ProviderPriority
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

logger = get_logger(__name__)


class ConfigProvider(Provider):
    """Configuration loading, models, and sources DI provider.

    This provider handles loading configuration from various sources (YAML, Env)
    and registering the configuration instance into the DI container.

    All config classes are backed by ``DomainModel`` (stdlib dataclasses).
    Environment variable reading is handled by ``EnvironmentConfigSource``,
    which is always added as a source.
    """

    name = "config"
    priority = ProviderPriority.CRITICAL

    def __init__(
        self,
        config_class: type[Any] = LexigramConfig,
        sources: list[Any] | None = None,
        env_prefix: str = "",
        extensions: dict[str, type] | None = None,
    ) -> None:
        super().__init__()
        self.config_class = config_class
        self.sources = sources
        self.env_prefix = env_prefix
        self._registry = ConfigRegistry()
        if extensions:
            for name, cls in extensions.items():
                self._registry.register(name, cls)
        self._config_instance: Any | None = None

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Load configuration and register as a singleton."""
        if self._config_instance is None:
            from pathlib import Path

            loader = ConfigLoader()

            # 1. Check for default application.yaml in CWD
            yaml_path = Path.cwd() / "application.yaml"
            try:
                if yaml_path.exists():
                    loader.add_source(FileConfigSource(yaml_path))
            except (FileNotFoundError, OSError) as e:
                logger.debug("no_default_config", path=str(yaml_path), reason=str(e))

            # 2. Add custom sources if provided
            if self.sources:
                for source in self.sources:
                    loader.add_source(source)

            # 3. Always add env vars
            prefix = self.env_prefix or "LEX_"
            loader.add_source(EnvironmentConfigSource(prefix))

            # 4. Load and apply registry
            self._config_instance = loader.load_sync(self.config_class)
            self._registry.apply_to_instance(self._config_instance)

        # 5. Register with multiple keys for compatibility
        container.singleton(self.config_class, instance=self._config_instance)
        container.singleton(ConfigProtocol, instance=self._config_instance)
        # Also register as LexigramConfig if it's a subclass of LexigramConfig
        # and not already registered as the main config_class.
        if self.config_class is not LexigramConfig and isinstance(
            self._config_instance, LexigramConfig
        ):
            container.singleton(LexigramConfig, instance=self._config_instance)

        container.singleton("config", instance=self._config_instance)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """No boot-time work required for the config module."""

    async def shutdown(self) -> None:
        """No resources to release for the config module."""

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report config loading status."""
        return HealthCheckResult(
            component="config",
            status=HealthStatus.HEALTHY,
            details={"config_loaded": self._config_instance is not None},
        )


__all__ = ["ConfigProvider"]
