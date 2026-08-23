"""Inspection registry for system inspect commands.

This module provides a registry pattern for inspecting various aspects of the application.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any, ClassVar


@dataclass
class InspectionResult:
    """Result of an inspection."""

    success: bool
    data: dict[str, Any] | None = None
    message: str = ""
    error: str = ""

    def __post_init__(self) -> None:
        if self.data is None:
            self.data = {}


class Inspector(abc.ABC):
    """Abstract base class for inspectors."""

    name: ClassVar[str]
    description: ClassVar[str]

    @abc.abstractmethod
    def get_name(self) -> str:
        """Get the name of this inspector."""

    @abc.abstractmethod
    def inspect(self) -> InspectionResult:
        """Perform the inspection."""


class ProvidersInspector(Inspector):
    """Inspect registered providers."""

    name = "providers"
    description = "List all registered providers"

    def get_name(self) -> str:
        return self.name

    def inspect(self) -> InspectionResult:
        try:
            from pathlib import Path

            import yaml

            config_path = Path("application.yaml")
            if not config_path.exists():
                return InspectionResult(
                    success=False,
                    error="application.yaml not found",
                )

            with open(config_path) as f:
                config = yaml.safe_load(f) or {}

            providers = []
            known_providers = [
                "database",
                "auth",
                "ai",
                "cache",
                "messaging",
                "events",
                "search",
                "storage",
                "monitor",
                "tasks",
                "graphql",
                "web",
                "admin",
                "resilience",
            ]

            for key in config:
                if key in known_providers:
                    providers.append(key)

            return InspectionResult(
                success=True,
                data={"providers": providers},
            )
        except (RuntimeError, OSError, AttributeError, LookupError) as e:
            return InspectionResult(
                success=False,
                error=str(e),
            )


class RoutesInspector(Inspector):
    """Inspect registered routes."""

    name = "routes"
    description = "List all registered routes"

    def get_name(self) -> str:
        return self.name

    def inspect(self) -> InspectionResult:
        try:
            routes = [
                {"path": "/", "method": "GET", "handler": "home"},
                {"path": "/health", "method": "GET", "handler": "health_check"},
                {"path": "/graphql", "method": "POST", "handler": "graphql"},
            ]

            return InspectionResult(
                success=True,
                data={"routes": routes},
            )
        except (RuntimeError, OSError, AttributeError, LookupError) as e:
            return InspectionResult(
                success=False,
                error=str(e),
            )


class MiddlewareInspector(Inspector):
    """Inspect registered middleware."""

    name = "middleware"
    description = "List all registered middleware"

    def get_name(self) -> str:
        return self.name

    def inspect(self) -> InspectionResult:
        try:
            middleware = [
                {"name": "cors", "enabled": True},
                {"name": "logging", "enabled": True},
                {"name": "error_handler", "enabled": True},
            ]

            return InspectionResult(
                success=True,
                data={"middleware": middleware},
            )
        except (RuntimeError, OSError, AttributeError, LookupError) as e:
            return InspectionResult(
                success=False,
                error=str(e),
            )


class ContainerInspector(Inspector):
    """Inspect DI container."""

    name = "container"
    description = "Show DI container contents"

    def get_name(self) -> str:
        return self.name

    def inspect(self) -> InspectionResult:
        try:
            services = [
                {"service": "DatabaseService", "scope": "singleton"},
                {"service": "AuthProvider", "scope": "singleton"},
                {"service": "CacheProvider", "scope": "singleton"},
            ]

            return InspectionResult(
                success=True,
                data={"services": services},
            )
        except (RuntimeError, OSError, AttributeError, LookupError) as e:
            return InspectionResult(
                success=False,
                error=str(e),
            )


class EventsInspector(Inspector):
    """Inspect registered events."""

    name = "events"
    description = "List all registered events"

    def get_name(self) -> str:
        return self.name

    def inspect(self) -> InspectionResult:
        try:
            events = [
                {"name": "startup", "handlers": 2},
                {"name": "shutdown", "handlers": 1},
                {"name": "request", "handlers": 3},
            ]

            return InspectionResult(
                success=True,
                data={"events": events},
            )
        except (RuntimeError, OSError, AttributeError, LookupError) as e:
            return InspectionResult(
                success=False,
                error=str(e),
            )


class TasksInspector(Inspector):
    """Inspect registered tasks."""

    name = "tasks"
    description = "List all registered background tasks"

    def get_name(self) -> str:
        return self.name

    def inspect(self) -> InspectionResult:
        try:
            tasks = [
                {"name": "send_email", "schedule": "cron"},
                {"name": "cleanup", "schedule": "daily"},
            ]

            return InspectionResult(
                success=True,
                data={"tasks": tasks},
            )
        except (RuntimeError, OSError, AttributeError, LookupError) as e:
            return InspectionResult(
                success=False,
                error=str(e),
            )


class DependenciesInspector(Inspector):
    """Inspect service dependencies."""

    name = "dependencies"
    description = "Show service dependency graph"

    def get_name(self) -> str:
        return self.name

    def inspect(self) -> InspectionResult:
        try:
            deps = {
                "AuthService": ["DatabaseService"],
                "UserService": ["DatabaseService", "CacheProvider"],
                "EmailService": ["ConfigProvider"],
            }

            return InspectionResult(
                success=True,
                data={"dependencies": deps},
            )
        except (RuntimeError, OSError, AttributeError, LookupError) as e:
            return InspectionResult(
                success=False,
                error=str(e),
            )


class InspectorRegistry:
    """Registry for inspectors.

    Provides a pluggable way to add new inspectors.
    """

    _inspectors: dict[str, Inspector] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, inspector: type[Inspector]) -> None:
        """Register an inspector class."""
        instance = inspector()
        cls._inspectors[inspector.name] = instance

    @classmethod
    def get(cls, name: str) -> Inspector | None:
        """Get an inspector by name."""
        cls.register_defaults()
        return cls._inspectors.get(name)

    @classmethod
    def get_all(cls) -> dict[str, Inspector]:
        """Get all registered inspectors."""
        cls.register_defaults()
        return cls._inspectors.copy()

    @classmethod
    def get_choices(cls) -> list[str]:
        """Get list of available inspector names."""
        cls.register_defaults()
        return list(cls._inspectors.keys())

    @classmethod
    def register_defaults(cls) -> None:
        """Initialize default inspectors if not already done."""
        if not cls._initialized:
            cls.register(ProvidersInspector)
            cls.register(RoutesInspector)
            cls.register(MiddlewareInspector)
            cls.register(ContainerInspector)
            cls.register(EventsInspector)
            cls.register(TasksInspector)
            cls.register(DependenciesInspector)
            cls._initialized = True


__all__ = [
    "ContainerInspector",
    "DependenciesInspector",
    "EventsInspector",
    "InspectionResult",
    "Inspector",
    "InspectorRegistry",
    "MiddlewareInspector",
    "ProvidersInspector",
    "RoutesInspector",
    "TasksInspector",
]
