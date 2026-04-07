"""Presets registry for application presets.

This module provides a registry pattern for application presets.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, ClassVar


@dataclass
class Preset:
    """A preset configuration of providers."""

    name: str
    description: str
    packages: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)


class PresetDefinition(abc.ABC):
    """Abstract base class for preset definitions."""

    name: ClassVar[str]
    description: ClassVar[str]
    packages: ClassVar[list[str]] = []
    config: ClassVar[dict[str, Any]] = {}

    @abc.abstractmethod
    def get_preset(self) -> Preset:
        """Get the preset configuration."""


class WebAPIPreset(PresetDefinition):
    """Basic web API preset."""

    name = "web-api"
    description = "Basic web API with HTTP routing and middleware"
    packages = ["lexigram", "lexigram-web", "lexigram-sql"]
    config = {
        "web": {"host": "0.0.0.0", "port": 8000},
        "database": {"url": "sqlite:///./dev.db"},
    }

    def get_preset(self) -> Preset:
        return Preset(
            name=self.name,
            description=self.description,
            packages=self.packages.copy(),
            config=self.config.copy(),
        )


class GraphQLPreset(PresetDefinition):
    """GraphQL API preset."""

    name = "graphql"
    description = "GraphQL API with web framework"
    packages = ["lexigram", "lexigram-web", "lexigram-sql", "lexigram-graphql"]
    config = {
        "web": {"host": "0.0.0.0", "port": 8000},
        "database": {"url": "sqlite:///./dev.db"},
        "graphql": {"path": "/graphql"},
    }

    def get_preset(self) -> Preset:
        return Preset(
            name=self.name,
            description=self.description,
            packages=self.packages.copy(),
            config=self.config.copy(),
        )


class WorkerPreset(PresetDefinition):
    """Background worker preset."""

    name = "worker"
    description = "Background job processor"
    packages = ["lexigram", "lexigram-sql", "lexigram-tasks", "lexigram-queue"]
    config = {
        "database": {"url": "sqlite:///./worker.db"},
    }

    def get_preset(self) -> Preset:
        return Preset(
            name=self.name,
            description=self.description,
            packages=self.packages.copy(),
            config=self.config.copy(),
        )


class FullStackPreset(PresetDefinition):
    """Full-stack application preset."""

    name = "fullstack"
    description = "Complete web application with database, auth, cache, and messaging"
    packages = [
        "lexigram",
        "lexigram-web",
        "lexigram-sql",
        "lexigram-auth",
        "lexigram-admin",
        "lexigram-cache",
        "lexigram-tasks",
        "lexigram-monitoring",
    ]
    config = {
        "web": {"host": "0.0.0.0", "port": 8000},
        "database": {"url": "sqlite:///./app.db"},
        "auth": {"enabled": True},
    }

    def get_preset(self) -> Preset:
        return Preset(
            name=self.name,
            description=self.description,
            packages=self.packages.copy(),
            config=self.config.copy(),
        )


class MinimalPreset(PresetDefinition):
    """Minimal preset."""

    name = "minimal"
    description = "Bare minimum Lexigram application"
    packages = ["lexigram"]
    config = {}

    def get_preset(self) -> Preset:
        return Preset(
            name=self.name,
            description=self.description,
            packages=self.packages.copy(),
            config=self.config.copy(),
        )


class MicroservicePreset(PresetDefinition):
    """Microservice preset."""

    name = "microservice"
    description = "Microservice with CQRS, database, and monitoring"
    packages = ["lexigram", "lexigram-sql", "lexigram-events", "lexigram-monitoring"]
    config = {
        "database": {"url": "sqlite:///./service.db"},
    }

    def get_preset(self) -> Preset:
        return Preset(
            name=self.name,
            description=self.description,
            packages=self.packages.copy(),
            config=self.config.copy(),
        )


class PresetRegistry:
    """Registry for application presets.

    Provides a pluggable way to add new presets.
    """

    _presets: dict[str, Preset] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, preset_class: type[PresetDefinition]) -> None:
        """Register a preset class."""
        instance = preset_class()
        preset = instance.get_preset()
        cls._presets[preset.name] = preset

    @classmethod
    def get(cls, name: str) -> Preset | None:
        """Get a preset by name."""
        cls.register_defaults()
        return cls._presets.get(name)

    @classmethod
    def get_all(cls) -> dict[str, Preset]:
        """Get all registered presets."""
        cls.register_defaults()
        return cls._presets.copy()

    @classmethod
    def get_choices(cls) -> list[str]:
        """Get list of available preset names."""
        cls.register_defaults()
        return list(cls._presets.keys())

    @classmethod
    def register_defaults(cls) -> None:
        """Initialize default presets if not already done."""
        if not cls._initialized:
            cls.register(WebAPIPreset)
            cls.register(GraphQLPreset)
            cls.register(WorkerPreset)
            cls.register(FullStackPreset)
            cls.register(MinimalPreset)
            cls.register(MicroservicePreset)
            cls._initialized = True


__all__ = [
    "FullStackPreset",
    "GraphQLPreset",
    "MicroservicePreset",
    "MinimalPreset",
    "Preset",
    "PresetDefinition",
    "PresetRegistry",
    "WebAPIPreset",
    "WorkerPreset",
]
