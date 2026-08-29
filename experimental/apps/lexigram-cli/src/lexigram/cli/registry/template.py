"""Project template registry for the new command.

This module provides a registry pattern for project templates.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from pathlib import Path



@dataclass
class TemplateConfig:
    """Configuration for a project template."""

    name: str
    description: str = ""
    packages: list[str] = field(default_factory=list)
    files: dict[str, str] = field(default_factory=dict)
    env_vars: dict[str, str] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)


class ProjectTemplate(abc.ABC):
    """Abstract base class for project templates."""

    name: ClassVar[str]
    description: ClassVar[str]
    packages: ClassVar[list[str]] = []
    files: ClassVar[dict[str, str]] = {}

    @abc.abstractmethod
    def get_config(self) -> TemplateConfig:
        """Get the template configuration."""

    def get_dependencies(self) -> list[str]:
        """Get the list of dependencies for this template."""
        return self.packages.copy()


class MinimalTemplate(ProjectTemplate):
    """Minimal template with just the core framework."""

    name = "minimal"
    description = "Bare minimum Lexigram application"
    packages = [
        "lexigram",
    ]

    def get_config(self) -> TemplateConfig:
        return TemplateConfig(
            name=self.name,
            description=self.description,
            packages=self.packages,
        )


class WebAPITemplate(ProjectTemplate):
    """REST API template."""

    name = "web-api"
    description = "REST API with web framework"
    packages = [
        "lexigram",
        "lexigram-web",
        "lexigram-sql",
    ]

    def get_config(self) -> TemplateConfig:
        return TemplateConfig(
            name=self.name,
            description=self.description,
            packages=self.packages,
        )


class GraphQLTemplate(ProjectTemplate):
    """GraphQL API template."""

    name = "graphql"
    description = "GraphQL API with web framework"
    packages = [
        "lexigram",
        "lexigram-web",
        "lexigram-sql",
        "lexigram-graphql",
    ]

    def get_config(self) -> TemplateConfig:
        return TemplateConfig(
            name=self.name,
            description=self.description,
            packages=self.packages,
        )


class WorkerTemplate(ProjectTemplate):
    """Background worker template."""

    name = "worker"
    description = "Background job processor"
    packages = [
        "lexigram",
        "lexigram-sql",
        "lexigram-tasks",
        "lexigram-queue",
    ]

    def get_config(self) -> TemplateConfig:
        return TemplateConfig(
            name=self.name,
            description=self.description,
            packages=self.packages,
        )


class FullStackTemplate(ProjectTemplate):
    """Full-stack application template."""

    name = "fullstack"
    description = "Full application with auth, admin, and more"
    packages = [
        "lexigram",
        "lexigram-web",
        "lexigram-sql",
        "lexigram-auth",
        "lexigram-admin",
        "lexigram-cache",
        "lexigram-tasks",
        "lexigram-monitor",
    ]

    def get_config(self) -> TemplateConfig:
        return TemplateConfig(
            name=self.name,
            description=self.description,
            packages=self.packages,
        )


class TemplateRegistry:
    """Registry for project templates.

    Provides a pluggable way to add new project templates.
    """

    _templates: dict[str, ProjectTemplate] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, template: type[ProjectTemplate]) -> None:
        """Register a project template class."""
        instance = template()
        cls._templates[template.name] = instance

    @classmethod
    def get(cls, name: str) -> ProjectTemplate | None:
        """Get a template by name."""
        cls.register_defaults()
        return cls._templates.get(name)

    @classmethod
    def get_all(cls) -> dict[str, ProjectTemplate]:
        """Get all registered templates."""
        cls.register_defaults()
        return cls._templates.copy()

    @classmethod
    def get_choices(cls) -> list[str]:
        """Get list of available template names."""
        cls.register_defaults()
        return list(cls._templates.keys())

    @classmethod
    def register_defaults(cls) -> None:
        """Initialize default templates if not already done."""
        if not cls._initialized:
            cls.register(MinimalTemplate)
            cls.register(WebAPITemplate)
            cls.register(GraphQLTemplate)
            cls.register(WorkerTemplate)
            cls.register(FullStackTemplate)
            cls._initialized = True


class ProjectBuilder:
    """Builder for creating new projects from templates.

    Delegates to the canonical :mod:`lexigram.cli.scaffold` renderer so the
    registry templates and ``lexigram new project --template`` produce the
    exact same, fully aligned project tree.
    """

    def __init__(self, template: ProjectTemplate | str):
        if isinstance(template, str):
            resolved = TemplateRegistry.get(template)
            if resolved is None:
                raise ValueError(f"Unknown template: {template}")
            self.template = resolved
        else:
            self.template = template

    def create_project(
        self,
        project_name: str,
        target_dir: Path,
        options: dict[str, Any] | None = None,
    ) -> list[Path]:
        """Create a new project from the template.

        Args:
            project_name: Project name (dashes become underscores).
            target_dir: Destination directory.
            options: Reserved for feature toggles (currently unused).

        Returns:
            The list of created file paths.

        Raises:
            ValueError: Directory is not empty or the template is unknown.
        """
        from lexigram.cli.scaffold import render_project

        return render_project(self.template.name, project_name, target_dir)


__all__ = [
    "FullStackTemplate",
    "GraphQLTemplate",
    "MinimalTemplate",
    "ProjectBuilder",
    "ProjectTemplate",
    "TemplateConfig",
    "TemplateRegistry",
    "WebAPITemplate",
    "WorkerTemplate",
]
