"""Provider registry and installer for the add command.

Provides lookup/discovery over the provider catalog and utilities to
install provider packages and merge their config into application.yaml.
"""

from __future__ import annotations

import subprocess

from lexigram.cli.registry.provider_catalog import (
    AdminProvider,
    AIProvider,
    AuthProvider,
    CacheProvider,
    CommonProvider,
    ConnectProvider,
    DatabaseService,
    EventsProvider,
    GraphQLProvider,
    MessagingProvider,
    MonitoringProvider,
    MonitorProvider,
    NotificationProvider,
    Provider,
    QueueProvider,
    ResilienceProvider,
    SearchProvider,
    StorageProvider,
    TasksProvider,
    TestingProvider,
    WebProvider,
)


class ProviderRegistry:
    """Registry for Lexigram providers.

    Provides a pluggable way to add new providers.
    """

    def __init__(self) -> None:
        self._providers: dict[str, Provider] = {}
        self._initialized: bool = False

    def register(self, provider: type[Provider]) -> None:
        """Register a provider class."""
        instance = provider()
        self._providers[provider.name] = instance

    def get(self, name: str) -> Provider | None:
        """Get a provider by name."""
        self.register_defaults()
        return self._providers.get(name)

    def get_all(self) -> dict[str, Provider]:
        """Get all registered providers."""
        self.register_defaults()
        return self._providers.copy()

    def get_choices(self) -> list[str]:
        """Get list of available provider names."""
        self.register_defaults()
        return list(self._providers.keys())

    def register_defaults(self) -> None:
        """Initialize default providers if not already done."""
        if not self._initialized:
            self.register(DatabaseService)
            self.register(AuthProvider)
            self.register(AIProvider)
            self.register(CacheProvider)
            self.register(QueueProvider)
            self.register(MessagingProvider)
            self.register(NotificationProvider)
            self.register(EventsProvider)
            self.register(SearchProvider)
            self.register(StorageProvider)
            self.register(MonitorProvider)
            self.register(TasksProvider)
            self.register(GraphQLProvider)
            self.register(ResilienceProvider)
            self.register(MonitoringProvider)
            self.register(WebProvider)
            self.register(AdminProvider)
            self.register(ConnectProvider)
            self.register(CommonProvider)
            self.register(TestingProvider)
            self._initialized = True


class ProviderInstaller:
    """Utility for installing providers."""

    @staticmethod
    def install_provider(provider: Provider) -> bool:
        """Install a provider package using uv."""
        info = provider.get_info()
        try:
            result = subprocess.run(  # noqa: S603 — argv list, no shell
                ["uv", "add", info.package],  # noqa: S607 — static CLI tool on PATH (operator-invoked)
                check=False,
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except (RuntimeError, OSError, AttributeError, LookupError):
            return False

    @staticmethod
    def add_provider_config(
        provider: Provider,
        config_path: str = "application.yaml",
    ) -> bool:
        """Add provider configuration to application.yaml."""
        from pathlib import Path

        import yaml

        info = provider.get_info()
        config_file = Path(config_path)

        if not config_file.exists():
            return False

        try:
            with open(config_file) as f:
                config_data = yaml.safe_load(f) or {}

            for key, value in info.config.items():
                if key not in config_data:
                    config_data[key] = value

            with open(config_file, "w") as f:
                yaml.dump(config_data, f, sort_keys=False)

            return True
        except (RuntimeError, OSError, AttributeError, LookupError):
            return False


__all__ = ["ProviderInstaller", "ProviderRegistry"]
