"""Provider registry for the add command.

This module provides a registry pattern for Lexigram providers/packages.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
import subprocess
from typing import Any, ClassVar


@dataclass
class ProviderInfo:
    """Information about a Lexigram provider."""

    name: str
    package: str
    description: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    optional_dependencies: list[str] = field(default_factory=list)


class Provider(abc.ABC):
    """Abstract base class for providers."""

    name: ClassVar[str]
    package: ClassVar[str]
    description: ClassVar[str]
    config: ClassVar[dict[str, Any]] = {}

    @abc.abstractmethod
    def get_info(self) -> ProviderInfo:
        """Get provider information."""


class DatabaseService(Provider):
    """Database provider."""

    name = "database"
    package = "lexigram-sql"
    description = "Database ORM and migrations"
    config = {
        "database": {
            "url": "sqlite:///./dev.db",
            "echo": False,
        },
    }

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self.name,
            package=self.package,
            description=self.description,
            config=self.config,
        )


class AuthProvider(Provider):
    """Authentication provider."""

    name = "auth"
    package = "lexigram-auth"
    description = "Authentication and authorization"
    config = {
        "auth": {
            "secret": "your-secure-secret-key-here",
            "algorithm": "HS256",
            "expire_minutes": 60,
        },
    }

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self.name,
            package=self.package,
            description=self.description,
            config=self.config,
        )


class AIProvider(Provider):
    """AI/LLM provider."""

    name = "ai"
    package = "lexigram-ai"
    description = "AI and LLM integration"
    config = {
        "ai": {
            "provider": "ollama",
            "model": "llama3",
        },
    }

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self.name,
            package=self.package,
            description=self.description,
            config=self.config,
        )


class CacheProvider(Provider):
    """Caching provider."""

    name = "cache"
    package = "lexigram-cache"
    description = "Caching layer"
    config = {
        "cache": {
            "backend": "memory",
        },
    }

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self.name,
            package=self.package,
            description=self.description,
            config=self.config,
        )


class QueueProvider(Provider):
    """Queue/broker provider."""

    name = "queue"
    package = "lexigram-queue"
    description = "Message broker and queues"
    config = {
        "queue": {
            "broker": "redis",
            "url": "redis://localhost:6379/0",
        },
    }

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self.name,
            package=self.package,
            description=self.description,
            config=self.config,
        )


class MessagingProvider(Provider):
    """Messaging provider (notifications + email)."""

    name = "messaging"
    package = "lexigram-notification"
    description = "Email and notification delivery"
    config = {
        "notification": {
            "backend": "smtp",
            "from_email": "noreply@example.com",
        },
    }

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self.name,
            package=self.package,
            description=self.description,
            config=self.config,
        )


class NotificationProvider(Provider):
    """Notification provider."""

    name = "notification"
    package = "lexigram-notification"
    description = "SMS + push notifications"
    config = {
        "notification": {
            "sms_backend": "twilio",
            "push_backend": "fcm",
        },
    }

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self.name,
            package=self.package,
            description=self.description,
            config=self.config,
        )


class EventsProvider(Provider):
    """Events provider."""

    name = "events"
    package = "lexigram-events"
    description = "Event handling and dispatch"
    config = {
        "events": {
            "store": "postgres",
        },
    }

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self.name,
            package=self.package,
            description=self.description,
            config=self.config,
        )


class SearchProvider(Provider):
    """Search provider."""

    name = "search"
    package = "lexigram-search"
    description = "Full-text search"
    config = {
        "search": {
            "backend": "elasticsearch",
            "url": "http://localhost:9200",
        },
    }

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self.name,
            package=self.package,
            description=self.description,
            config=self.config,
        )


class StorageProvider(Provider):
    """Storage provider."""

    name = "storage"
    package = "lexigram-storage"
    description = "File storage"
    config = {
        "storage": {
            "driver": "local",
            "root": "./storage",
        },
    }

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self.name,
            package=self.package,
            description=self.description,
            config=self.config,
        )


class MonitorProvider(Provider):
    """Monitoring provider."""

    name = "monitor"
    package = "lexigram-monitor"
    description = "Monitoring and observability"
    config = {
        "monitor": {
            "enabled": True,
        },
    }

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self.name,
            package=self.package,
            description=self.description,
            config=self.config,
        )


class TasksProvider(Provider):
    """Background tasks provider."""

    name = "tasks"
    package = "lexigram-tasks"
    description = "Background task processing"
    config = {
        "tasks": {
            "worker": "celery",
        },
    }

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self.name,
            package=self.package,
            description=self.description,
            config=self.config,
        )


class GraphQLProvider(Provider):
    """GraphQL provider."""

    name = "graphql"
    package = "lexigram-graphql"
    description = "GraphQL API support"
    config = {
        "graphql": {
            "path": "/graphql",
            "graphiql": True,
        },
    }

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self.name,
            package=self.package,
            description=self.description,
            config=self.config,
        )


class ResilienceProvider(Provider):
    """Resilience patterns provider.

    Resilience is now part of the core *lexigram* package; the provider
    exists primarily for configuration metadata rather than pulling in an
    external distribution.
    """

    name = "resilience"
    package = "lexigram"  # core lexigram package contains resilience
    description = "Resilience and fault tolerance"
    config = {
        "resilience": {
            "timeout": 30,
            "retry_count": 3,
        },
    }

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self.name,
            package=self.package,
            description=self.description,
            config=self.config,
        )


class MonitoringProvider(Provider):
    """Monitoring and observability provider."""

    name = "monitoring"
    package = "lexigram-monitoring"
    description = "Monitoring and observability"
    config = {
        "monitoring": {
            "service_name": "my-app",
            "otel": {
                "enabled": True,
                "exporter": "otlp",
            },
        },
    }

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self.name,
            package=self.package,
            description=self.description,
            config=self.config,
        )


class WebProvider(Provider):
    """Web framework provider."""

    name = "web"
    package = "lexigram-web"
    description = "Web framework"
    config = {
        "web": {
            "host": "0.0.0.0",  # noqa: S104 — provider config template default
            "port": 8000,
        },
    }

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self.name,
            package=self.package,
            description=self.description,
            config=self.config,
        )


class AdminProvider(Provider):
    """Admin panel provider."""

    name = "admin"
    package = "lexigram-admin"
    description = "Admin panel"
    config = {
        "admin": {
            "path": "/admin",
            "theme": "dark",
        },
    }

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self.name,
            package=self.package,
            description=self.description,
            config=self.config,
        )


class ConnectProvider(Provider):
    """External connections provider."""

    name = "http"
    package = "lexigram"
    description = "HTTP client (built into lexigram core)"
    config = {
        "connect": {
            "base_url": "http://localhost:8080",
        },
    }

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self.name,
            package=self.package,
            description=self.description,
            config=self.config,
        )


class CommonProvider(Provider):
    """Common utilities provider."""

    name = "common"
    package = "lexigram-common"
    description = "Core utilities"
    config = {
        "common": {
            "logging": {"level": "INFO"},
        },
    }

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self.name,
            package=self.package,
            description=self.description,
            config=self.config,
        )


class TestingProvider(Provider):
    """Testing utilities provider."""

    name = "testing"
    package = "lexigram-testing"
    description = "Testing utilities"
    config = {
        "testing": {
            "db_reuse": True,
        },
    }

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            name=self.name,
            package=self.package,
            description=self.description,
            config=self.config,
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


__all__ = [
    "AIProvider",
    "AdminProvider",
    "AuthProvider",
    "CacheProvider",
    "CommonProvider",
    "ConnectProvider",
    "DatabaseService",
    "EventsProvider",
    "GraphQLProvider",
    "MessagingProvider",
    "MonitorProvider",
    "MonitoringProvider",
    "NotificationProvider",
    "Provider",
    "ProviderInfo",
    "ProviderInstaller",
    "ProviderRegistry",
    "QueueProvider",
    "ResilienceProvider",
    "SearchProvider",
    "StorageProvider",
    "TasksProvider",
    "TestingProvider",
    "WebProvider",
]
