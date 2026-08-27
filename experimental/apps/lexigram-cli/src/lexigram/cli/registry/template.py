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
    """Builder for creating new projects from templates."""

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
    ) -> None:
        """Create a new project from the template."""
        options = options or {}

        if target_dir.exists() and any(target_dir.iterdir()):
            raise ValueError(f"Directory {target_dir} is not empty")

        target_dir.mkdir(parents=True, exist_ok=True)

        package_name = project_name.replace("-", "_")

        self._create_project_files(project_name, package_name, target_dir, options)
        self._create_pyproject_toml(project_name, package_name, target_dir)
        self._create_lexigram_yaml(project_name, target_dir)
        self._create_env_example(target_dir)

    def _create_project_files(
        self,
        project_name: str,
        package_name: str,
        target_dir: Path,
        options: dict[str, Any],
    ) -> None:
        src_dir = target_dir / "src" / package_name
        src_dir.mkdir(parents=True, exist_ok=True)

        (src_dir / "__init__.py").write_text(f'"""{project_name} package."""\n')

        app_py = src_dir / "app.py"
        if options.get("auth"):
            app_py.write_text(_APP_WITH_AUTH_TEMPLATE.format(package_name=package_name))
        else:
            app_py.write_text(_APP_TEMPLATE.format(package_name=package_name))

        controllers_dir = src_dir / "api" / "v1" / "controllers"
        controllers_dir.mkdir(parents=True, exist_ok=True)
        (controllers_dir / "__init__.py").write_text("")

        models_dir = src_dir / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        (models_dir / "__init__.py").write_text("")

        services_dir = src_dir / "services"
        services_dir.mkdir(parents=True, exist_ok=True)
        (services_dir / "__init__.py").write_text("")

    def _create_pyproject_toml(
        self,
        project_name: str,
        package_name: str,
        target_dir: Path,
    ) -> None:
        deps = self.template.get_dependencies()
        deps_str = '\n    "'.join(deps) if deps else ""

        content = _PYPROJECT_TEMPLATE.format(
            project_name=project_name,
            package_name=package_name,
            dependencies=deps_str,
        )
        (target_dir / "pyproject.toml").write_text(content)

    def _create_lexigram_yaml(
        self,
        project_name: str,
        target_dir: Path,
    ) -> None:
        content = _LEX_YAML_TEMPLATE.format(project_name=project_name)
        (target_dir / "application.yaml").write_text(content)

    def _create_env_example(self, target_dir: Path) -> None:
        (target_dir / ".env.example").write_text(_ENV_EXAMPLE_TEMPLATE)


_APP_TEMPLATE = '''"""Application entry point."""

from lexigram import App


def create_app() -> App:
    app = App(name="{package_name}")
    return app


app = create_app()


if __name__ == "__main__":
    from lexigram.web.server.runner import run_server
    run_server(app, host="0.0.0.0", port=8000)
'''

_APP_WITH_AUTH_TEMPLATE = '''"""Application entry point with authentication."""

from lexigram import App
from lexigram.cli.registry.provider import AuthProvider


def create_app() -> App:
    app = App(name="{package_name}")
    app.add_provider(AuthProvider())
    return app


app = create_app()


if __name__ == "__main__":
    from lexigram.web.server.runner import run_server
    run_server(app, host="0.0.0.0", port=8000)
'''

_PYPROJECT_TEMPLATE = """[project]
name = "{project_name}"
version = "0.1.0"
description = "A Lexigram application"
requires-python = ">=3.11"
dependencies = [
    "{dependencies}"
]

[project.optional-dependencies]
dev = [
    "pytest",
    "ruff",
    "mypy",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.lexigram]
module = "{package_name}.app:app"
"""

_LEX_YAML_TEMPLATE = """project:
  name: {project_name}
  version: "0.1.0"

logging:
  level: INFO
  format: json
"""

_ENV_EXAMPLE_TEMPLATE = """# Lexigram environment overrides (LEX_<SECTION>__<FIELD> syntax).
# Sections mirror application.yaml keys; env vars override matching keys.
# Copy to .env and uncomment what you need.

# Web server (web.server)
# LEX_WEB__SERVER__HOST=127.0.0.1
# LEX_WEB__SERVER__PORT=8000

# Logging (logging.level): DEBUG | INFO | WARNING | ERROR
# LEX_LEXIGRAM__LOGGING__LEVEL=DEBUG

# Database URL (consumed by lexigram-sql's config_key="sql" provider section;
# also set db.backend.url in application.yaml when adding SQL support)
# LEX_SQL__BACKEND__URL=postgresql://localhost/mydb

# Auth secret — set a real value before deploying with auth enabled
# LEX_AUTH__SECRET_KEY=change-me-in-production
"""


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
