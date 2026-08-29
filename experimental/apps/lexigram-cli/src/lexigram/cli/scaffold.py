"""Canonical Lexigram project scaffold.

Single source of truth for project bootstrapping:

- ``lexigram new project --template <name> --structure <s>`` (``commands/new.py``)
- ``ProjectBuilder.create_project`` (``registry/template.py``)
- scaffold alignment tests (``tests/unit/test_scaffold_alignment.py``)

Every generated file targets the **real** lexigram APIs (``Application``,
``LexigramConfig``, ``WebModule``, ``Controller``) and the **canonical
generator map** in :mod:`lexigram.cli.layout` — the component packages below
mirror ``lexigram gen`` output directories, so a scaffolded project and its
generators stay aligned in every structure:

    lexigram new project myapp --template web-api --structure structured
    cd myapp && pip install -e .
    lexigram gen controller users     # writes src/controllers/users_controller.py
    lexigram dev                      # WebModule auto-discovers it

The same renderer produces:

- ``minimal``    — single package; generators write inside ``src/<app>/``
- ``structured`` — generator-native sibling component packages (default)
- ``modular``    — bounded contexts + ``shared/`` + ``infrastructure/``

The generated ``application.yaml`` is validated by :class:`LexigramConfig`
(extra sections such as ``web`` / ``sql`` are consumed through the
``lexigram.config`` entry-point registry), and ``create_app()`` is a
standard composition root: bootable via ``lexigram dev`` / ``lexigram run``
and directly in pytest fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import textwrap

from lexigram.cli.layout import (
    MODULAR,
    ROOT_DIRS,
    STRUCTURED,
    STRUCTURES,
)
from lexigram.cli.layout import (
    component_packages as _layout_component_packages,
)
from lexigram.cli.layout import (
    root_output_dirs as _layout_root_output_dirs,
)

TEMPLATE_ALIASES = {
    "fullstack": "full",
}


@dataclass(frozen=True)
class ProjectTemplateSpec:
    """Declarative description of a project template."""

    name: str
    description: str
    dependencies: tuple[str, ...]
    features: frozenset[str] = frozenset()
    notes: tuple[str, ...] = field(default_factory=tuple)


def _spec(
    name: str,
    description: str,
    dependencies: tuple[str, ...],
    features: frozenset[str] = frozenset(),
    notes: tuple[str, ...] = (),
) -> ProjectTemplateSpec:
    return ProjectTemplateSpec(name, description, dependencies, features, notes)


TEMPLATES: dict[str, ProjectTemplateSpec] = {
    "minimal": _spec(
        "minimal",
        "Bare minimum Lexigram application",
        ("lexigram",),
    ),
    "api": _spec(
        "api",
        "REST API with the web framework",
        ("lexigram", "lexigram-web", "uvicorn"),
        frozenset({"web"}),
    ),
    "web-api": _spec(
        "web-api",
        "REST API with web + SQL persistence",
        ("lexigram", "lexigram-web", "lexigram-sql", "uvicorn"),
        frozenset({"web", "sql"}),
        (
            (
                "Controllers are auto-discovered from src/controllers; run "
                "`lexigram gen controller users` (does not need a restart)."
            ),
        ),
    ),
    "graphql": _spec(
        "graphql",
        "GraphQL API with web + SQL + GraphQL",
        ("lexigram", "lexigram-web", "lexigram-sql", "lexigram-graphql", "uvicorn"),
        frozenset({"web", "sql", "graphql"}),
        (
            (
                "Add serializers via `lexigram gen graphql product`; the schema "
                "package resolves through the project layout."
            ),
        ),
    ),
    "worker": _spec(
        "worker",
        "Background job processor",
        ("lexigram", "lexigram-queue", "lexigram-tasks", "lexigram-sql"),
        frozenset({"queue", "tasks", "sql"}),
        (
            (
                "Define jobs with `lexigram gen task nightly_report`, then start "
                "a worker with your preferred queue backend."
            ),
        ),
    ),
    "full": _spec(
        "full",
        "Full application with auth, admin, feature flags, cache, tasks, and SQL",
        (
            "lexigram",
            "lexigram-web",
            "lexigram-sql",
            "lexigram-auth",
            "lexigram-admin",
            "lexigram-features",
            "lexigram-cache",
            "lexigram-tasks",
            "uvicorn",
        ),
        frozenset({"web", "sql", "auth", "admin", "features", "cache", "tasks"}),
        (
            (
                "Auth ships with dev secret keys; replace LEX_AUTH__SECRET_KEY "
                "and LEX_AUTH__TOKEN__SECRET_KEY before deploying."
            ),
            (
                "Monitoring is not pre-wired: DatabaseModule and MonitorModule "
                "need an explicit import edge until the module graph allows it."
            ),
        ),
    ),
}
TEMPLATES["fullstack"] = TEMPLATES["full"]


def template_names() -> list[str]:
    """Return the available template names (aliases resolved)."""
    return sorted(set(TEMPLATES) - set(TEMPLATE_ALIASES)) + sorted(TEMPLATE_ALIASES)


def structure_names() -> list[str]:
    """Return the supported project structures."""
    return list(STRUCTURES)


def resolve_template(name: str) -> ProjectTemplateSpec:
    """Resolve a template name (following aliases)."""
    spec = TEMPLATES.get(TEMPLATE_ALIASES.get(name, name))
    if spec is None:
        raise ValueError(
            f"Unknown template {name!r}. Available: {', '.join(template_names())}"
        )
    return spec


def component_packages() -> dict[str, tuple[str, ...]]:
    """Return the canonical structured component package map (copy)."""
    return _layout_component_packages()


def root_output_dirs() -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Return generator root output directories (copy)."""
    return _layout_root_output_dirs()


def _package_line(package: str, generators: tuple[str, ...]) -> str:
    names = ", ".join(generators)
    return f'"""{package} package.\n\nWriters: {names} (lexigram gen)."""\n'


def _component_files(package_name: str, structure: str) -> dict[str, str]:
    """Component ``__init__.py`` files for a given structure."""
    files: dict[str, str] = {}
    if structure == STRUCTURED:
        for package, generators in _layout_component_packages().items():
            files[f"src/{package}/__init__.py"] = _package_line(package, generators)
    elif structure == MODULAR:
        from lexigram.cli.layout import COMPONENTS

        for component in COMPONENTS:
            if component.shared:
                path = f"src/{package_name}/shared/{component.modular}"
                files[f"{path}/__init__.py"] = _package_line(
                    f"{component.modular} (shared)", component.generators
                )
        for package, generators in ROOT_DIRS:
            files[f"{package}/__init__.py"] = _package_line(package, generators)
    # minimal: nothing pre-created; generators create their packages on demand.
    files[f"src/{package_name}/__init__.py"] = f'"""{package_name} package."""\n'
    files[f"src/{package_name}/py.typed"] = ""
    return files


def _application_yaml(project_name: str, spec: ProjectTemplateSpec) -> str:
    features = spec.features
    lines = [
        "# Lexigram configuration — validated by LexigramConfig plus the",
        "# `lexigram.config` entry-point models (web/sql sections are typed).",
        "# Every top-level section is typed; unknown keys are reported at boot.",
        "",
        f"app_name: {project_name}",
        "debug: false",
        "env: development",
        "",
        "logging:",
        "  level: INFO",
        "  json_format: false",
        "",
        "modules: []",
        "discovery:",
        "  auto_discover: false          # modules are wired explicitly in app.py",
        "  entry_point_group: lexigram.modules",
        "",
        "health:",
        "  include_details: true",
        "",
    ]
    if "web" in features:
        lines += [
            "web:",
            "  server:",
            "    host: 127.0.0.1",
            "    port: 8000",
            "  api_docs:",
            "    enabled: true",
            "",
        ]
    if "sql" in features:
        lines += [
            "sql:",
            "  enabled: true",
            "  backend:",
            "    url: sqlite:///./dev.db",
            "  pool:",
            "    min_size: 1",
            "    max_size: 5",
            "",
        ]
    if "auth" in features:
        lines += [
            "auth:",
            "  enabled: true",
            "  # Development keys — JWTConfig and AuthConfig both require one.",
            "  # Override with LEX_AUTH__SECRET_KEY / LEX_AUTH__TOKEN__SECRET_KEY.",
            f'  secret_key: "{project_name}-dev-auth-0123456789abcdef"',
            "  token:",
            f'    secret_key: "{project_name}-dev-token-0123456789abcdef"',
            "    algorithm: HS256",
            "",
        ]
    if "features" in features:
        lines += [
            "features:",
            "  enabled: true",
            "  default_enabled: true",
            "  cache_ttl: 60",
            "",
        ]
    if "cache" in features:
        lines += [
            "cache:",
            "  enabled: true",
            "  # backend defaults to an in-process memory store; add Redis via",
            "  # `backends` when you move to multi-worker deployments.",
            "",
        ]
    if "tasks" in features:
        lines += [
            "tasks:",
            "  enabled: true",
            "  # worker.backend defaults to the in-process scheduler in development.",
            "",
        ]
    if "queue" in features:
        lines += [
            "queue:",
            "  enabled: true",
            "  # In development the queue runs in-process; configure a broker",
            "  # (Redis, RabbitMQ, SQS) before scaling out.",
            "",
        ]
    if "monitor" in features:
        lines += [
            "monitor:",
            "  enabled: true",
            "  # OpenTelemetry/prometheus exporters are opt-in via env.",
            "",
        ]
    if "graphql" in features:
        lines += [
            "graphql:",
            "  enabled: true",
            "  path: /graphql",
            "  playground: true",
            "",
        ]
    return "\n".join(lines)


def _wheel_packages(package_name: str, structure: str) -> list[str]:
    """Wheel packages: the app package plus (structured) component packages."""
    packages = {f"src/{package_name}"}
    if structure == STRUCTURED:
        for relative in _layout_component_packages():
            packages.add(f"src/{relative.split('/')[0]}")
    return sorted(packages)


def _pyproject_toml(
    project_name: str,
    package_name: str,
    spec: ProjectTemplateSpec,
    structure: str,
) -> str:
    deps = "".join(f'    "{dep}",\n' for dep in spec.dependencies)
    wheel = "".join(
        f'    "{pkg}",\n' for pkg in _wheel_packages(package_name, structure)
    )
    return f"""[project]
name = "{project_name}"
version = "0.1.0"
description = "{spec.description}"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
{deps}]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
    "ruff>=0.6.0",
    "mypy>=1.10.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = [
{wheel}]

[tool.lexigram]
structure = "{structure}"
module = "{package_name}.app:app"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 88
target-version = "py311"
"""


def _module_imports(features: frozenset[str]) -> list[str]:
    """Alphabetical import lines for the feature modules."""
    names: list[str] = []
    if "web" in features:
        names.append("from lexigram.web import WebModule")
    if "sql" in features:
        names.append("from lexigram.sql import DatabaseModule")
    if "graphql" in features:
        names.append("from lexigram.graphql import GraphQLModule")
    if "auth" in features:
        names.append("from lexigram.auth import AuthModule")
    if "admin" in features:
        names.append("from lexigram.admin import AdminModule")
        names.append(
            "from lexigram.admin.config import AdminAuthConfig, AdminConfig, "
            "AdminSecurityConfig"
        )
    if "cache" in features:
        names.append("from lexigram.cache import CacheModule")
    if "features" in features:
        names.append("from lexigram.features import FeatureFlagsModule")
    if "tasks" in features:
        names.append("from lexigram.tasks import TasksModule")
    if "queue" in features:
        names.append("from lexigram.queue import QueueModule")
    if "monitor" in features:
        names.append("from lexigram.monitor import MonitorModule")
    names.sort()
    return names


def _feature_calls(
    features: frozenset[str],
    project_name: str,
    *,
    web_discover: str | None,
    include_graphql: bool = True,
) -> list[tuple[str, list[str]]]:
    """Ordered ``(comment, configure-call lines)`` pairs for the features.

    The web module is appended last so the server boots after every
    dependency is registered.  ``web_discover`` is the controller package
    discovered by ``WebModule`` (structure-dependent); when ``None`` the web
    call is omitted.  ``include_graphql=False`` skips the GraphQL call (used
    by the modular infrastructure layer, where the surface is wired by the
    composition root next to the web module).
    """
    calls: list[tuple[str, list[str]]] = []
    if "sql" in features:
        calls.append(
            (
                "# Persistence - reads the `sql:` section of application.yaml.",
                ["DatabaseModule.configure()"],
            )
        )
    if "auth" in features:
        calls.append(
            (
                "# Authentication - reads the `auth:` section.",
                ["AuthModule.configure()"],
            )
        )
    if "features" in features:
        calls.append(
            (
                "# Feature flags - read by the admin panel.",
                ["FeatureFlagsModule.configure()"],
            )
        )
    if "cache" in features:
        calls.append(
            (
                "# Caching - reads the `cache:` section.",
                ["CacheModule.configure()"],
            )
        )
    if "admin" in features:
        calls.append(
            (
                "# Admin dashboard - dev config skips the setup token.",
                [
                    "AdminModule.configure(",
                    "    config=AdminConfig(",
                    "        auth=AdminAuthConfig(",
                    "            security=AdminSecurityConfig(",
                    "                setup_token_optin_unsafe=True,",
                    "            ),",
                    "        ),",
                    "    ),",
                    "),",
                ],
            )
        )
    if "tasks" in features:
        calls.append(
            (
                "# Background tasks - reads the `tasks:` section.",
                ["TasksModule.configure()"],
            )
        )
    if "queue" in features:
        calls.append(
            (
                "# Message queue - reads the `queue:` section.",
                ["QueueModule.configure()"],
            )
        )
    if "monitor" in features:
        calls.append(
            (
                "# Metrics/tracing - reads the `monitor:` section.",
                ["MonitorModule.configure()"],
            )
        )
    if "graphql" in features and include_graphql:
        calls.append(
            (
                "# GraphQL - reads the `graphql:` section.",
                ["GraphQLModule.configure()"],
            )
        )
    if "web" in features and web_discover is not None:
        calls.append(
            (
                "# Web server - controllers written by `lexigram gen controller` are",
                [f'WebModule.configure(discover=["{web_discover}"])'],
            )
        )
    return calls


def _render_calls(calls: list[tuple[str, list[str]]], indent: int) -> list[str]:
    """Render ``(comment, lines)`` pairs at *indent* spaces."""
    rendered: list[str] = []
    for comment, call_lines in calls:
        rendered.append(f"{' ' * indent}# {comment.lstrip('#').strip()}")
        for index, line in enumerate(call_lines):
            if index == len(call_lines) - 1 and not line.rstrip().endswith(","):
                line = f"{line},"
            rendered.append(f"{' ' * indent}{line}")
    return rendered


def _render_infra_calls(calls: list[tuple[str, list[str]]]) -> list[str]:
    """Render feature calls as ``modules.append(...)`` statements."""
    rendered: list[str] = []
    for comment, call_lines in calls:
        rendered.append(f"    # {comment.lstrip('#').strip()}")
        rendered.append("    modules.append(")
        for line in call_lines:
            rendered.append(f"        {line}")
        rendered.append("    )")
    return rendered


def _infrastructure_py(package_name: str, spec: ProjectTemplateSpec) -> str:
    """Modular shared infrastructure layer (db, cache, events, monitoring)."""
    # web + graphql are application surfaces and are wired by the
    # composition root next to the module registry, never here.
    features = spec.features - {"web", "graphql"}
    imports = _module_imports(features)
    imports.append("from lexigram.di.module import DynamicModule")
    imports.sort()
    calls = _feature_calls(features, package_name, web_discover=None)
    body = _render_infra_calls(calls)
    return f'''"""Shared infrastructure wiring for {package_name}.

Feature modules configured here (persistence, auth, cache, tasks, queue,
monitoring) are registered before the web surface and the bounded contexts
in ``src/{package_name}/modules/``.  Replace or extend entries here when you
swap backends.
"""

from __future__ import annotations

{chr(10).join(imports)}


def infrastructure_modules() -> list[DynamicModule]:
    """Return the configured infrastructure modules for this application."""
    modules: list[DynamicModule] = []
{chr(10).join(body)}
    return modules
'''


def _modules_init(package_name: str, names: tuple[str, ...]) -> str:
    """Modular ``modules/__init__.py`` with the module registry."""
    imports = "\n".join(
        f"from {package_name}.modules.{slug} import {name}" for slug, name in names
    )
    entries = "".join(f"    {name},\n" for _slug, name in names)
    header = f"from __future__ import annotations\n\n{imports}\n\n" if imports else ""
    return f'''"""Application feature modules.

``lexigram new module <name>`` appends bounded contexts here; the composition
root registers every entry in ``MODULES``.  ``lexigram gen <component> <name>
--module <feature>`` writes module-local components into the matching module
package.
"""

{header}MODULES: list[type] = [
{entries}]
'''


def _module_boundary(
    module: str,
    class_name: str,
    title: str,
) -> str:
    """A modular feature-module boundary (``lexigram new module`` output)."""
    return f'''"""{module} module - bounded context.

``lexigram gen <component> <name> --module {module}`` writes module-local
components (controllers, models, services, repositories, ...) into this
package; ``lexigram gen`` without ``--module`` writes cross-cutting
components into the shared layer.
"""

from __future__ import annotations

from lexigram.di.module import Module, module


@module()
class {class_name}(Module):
    """{title} module."""
'''


def _module_protocols(module: str, title: str) -> str:
    """Public contract file for a feature module."""
    return f'''"""Public contracts for the {module} module.

Other modules import from here only — never from implementations.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class {title.replace(" ", "")}ServiceProtocol(Protocol):
    """Contract exposed by the {module} module."""
'''


def _module_provider(module: str, title: str) -> str:
    """DI provider file for a feature module."""
    return f'''"""DI provider for the {module} module."""

from __future__ import annotations

from lexigram.di.provider import Provider


class {title.replace(" ", "")}Provider(Provider):
    """Registers and boots {module} services."""
'''


def _module_scaffold_files(
    package_name: str, module: str, class_name: str
) -> dict[str, str]:
    """Bare files for ``lexigram new module <name>``."""
    title = class_name.removesuffix("Module").replace("_", " ").title()
    files: dict[str, str] = {
        f"src/{package_name}/modules/{module}/__init__.py": _module_boundary(
            module, class_name, title
        ),
        f"src/{package_name}/modules/{module}/protocols.py": _module_protocols(
            module, title
        ),
        f"src/{package_name}/modules/{module}/provider.py": _module_provider(
            module, title
        ),
        f"src/{package_name}/modules/{module}/services.py": (
            f'"""Application services for the {module} module."""\n'
        ),
    }
    return files


def _app_py(
    project_name: str,
    package_name: str,
    spec: ProjectTemplateSpec,
    structure: str,
) -> str:
    features = spec.features
    notes = "\n".join("\n".join(textwrap.wrap(note, width=88)) for note in spec.notes)
    if structure == MODULAR:
        imports = [
            "from lexigram.app import Application",
            "from lexigram.config import LexigramConfig",
        ]
        if "web" in features:
            imports.append("from lexigram.web import WebModule")
        if "graphql" in features:
            imports.append("from lexigram.graphql import GraphQLModule")
        imports.sort()
        local_imports = [
            f"from {package_name}.infrastructure import infrastructure_modules",
            f"from {package_name}.modules import MODULES",
        ]
        local_imports.sort()
        import_lines = "\n".join(imports) + "\n\n" + "\n".join(local_imports)
        lines = [
            "    application.add_modules(",
            "        [",
            "            *infrastructure_modules(),",
        ]
        if "graphql" in features:
            lines.append("            GraphQLModule.configure(),")
        lines.append("            *MODULES,")
        if "web" in features:
            lines.append(
                f'            WebModule.configure(discover=["{package_name}.modules"]),'
            )
        lines.append("        ]")
        lines.append("    )")
    else:
        imports = _module_imports(features)
        imports.extend(
            [
                "from lexigram.app import Application",
                "from lexigram.config import LexigramConfig",
            ]
        )
        imports.sort()
        discover = (
            "controllers" if structure == STRUCTURED else f"{package_name}.controllers"
        )
        calls = _feature_calls(features, project_name, web_discover=discover)
        lines = ["    application.add_modules(", "        ["]
        lines.extend(_render_calls(calls, 12))
        lines.append("        ]")
        lines.append("    )")
        import_lines = "\n".join(imports)

    return f'''"""{project_name} - composition root.

{notes}
"""
from __future__ import annotations

{import_lines}


def create_app(config: "LexigramConfig | None" = None) -> "Application":
    """Create the application in ``CREATED`` state (not yet started).

    Args:
        config: Optional pre-loaded config.  When ``None`` the framework
            auto-discovers ``application.yaml`` from the working directory.

    Returns:
        The bootable application instance.
    """
    application = Application(name="{project_name}", config=config)
{chr(10).join(lines)}
    return application


app = create_app()

__all__ = ["app", "create_app"]
'''


def _controller_module(project_name: str) -> str:
    return f'''"""Root API controllers.

`lexigram gen controller <name>` writes additional controllers into this
package; WebModule.configure(discover=["controllers"]) picks them up.

The framework already serves the canonical health probes at `/health`,
`/health/live`, `/health/ready`, and `/health/startup`; keep custom health
endpoints under a prefix such as `/api` so they do not shadow them.
"""
from __future__ import annotations

from typing import Any

from lexigram.web import Controller, get


class ApiController(Controller):
    """Root API endpoints."""

    @get("/")
    async def root(self) -> dict[str, Any]:
        """Service banner for the application root."""
        return {{"service": "{project_name}", "status": "ok"}}
'''


def _module_controller(package_name: str, module: str) -> str:
    """Sample controller for the modular ``users`` module."""
    return f'''"""Root API controllers for the {module} module.

`lexigram gen controller <name> --module {module}` writes additional
controllers here; WebModule.configure(discover=["{package_name}.modules"])
picks them up.
"""
from __future__ import annotations

from typing import Any

from lexigram.web import Controller, get


class ApiController(Controller):
    """Root API endpoints."""

    @get("/")
    async def root(self) -> dict[str, Any]:
        """Service banner for the application root."""
        return {{"service": "{package_name}", "status": "ok"}}
'''


def _conftest(project_name: str, package_name: str, spec: ProjectTemplateSpec) -> str:
    extras: list[str] = []
    if "web" in spec.features:
        extras = [
            "from lexigram.web import WebProvider",
            "from starlette.applications import Starlette",
        ]
    web_fixture = ""
    if "web" in spec.features:
        web_fixture = '''

@pytest.fixture
async def app(application: Application) -> Starlette:
    """Expose the Starlette app for httpx ASGI tests."""
    web = await application.container.resolve(WebProvider)
    return web.starlette
'''
    import_lines = [
        "import os",
        "import sys",
        "from pathlib import Path",
        "",
        "import pytest",
        "from lexigram.app import Application",
    ]
    import_lines.extend(extras)
    return f'''"""Pytest bootstrap for {project_name}."""
from __future__ import annotations

{chr(10).join(import_lines)}

_ROOT = Path(__file__).resolve().parents[1]
os.chdir(_ROOT)
sys.path.insert(0, str(_ROOT / "src"))

from {package_name}.app import create_app  # noqa: E402


@pytest.fixture
async def application() -> Application:
    """Boot the application for the duration of a test."""
    application = create_app()
    await application.start()
    try:
        yield application
    finally:
        await application.stop()
{web_fixture}
'''


def _test_app(spec: ProjectTemplateSpec, structure: str) -> str:
    web_bootable = "web" in spec.features and structure != "minimal"
    if web_bootable:
        return '''"""Smoke tests for the scaffolded application."""
from __future__ import annotations

import httpx


async def test_root(app) -> None:
    """GET / returns 200 with the service banner."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_readiness_probe(app) -> None:
    """The framework readiness probe is served and healthy."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
'''
    return '''"""Smoke tests for the scaffolded application."""
from __future__ import annotations

from lexigram.app import Application


async def test_boots(application: Application) -> None:
    """The application reaches the RUNNING state."""
    assert application.is_running
'''


def _readme(
    project_name: str,
    spec: ProjectTemplateSpec,
    structure: str,
    package_name: str,
) -> str:
    features = spec.features
    run = "lexigram dev" if "web" in features else "pytest"
    if structure == MODULAR:
        gen_example = "lexigram gen controller orders --module billing"
    elif structure == STRUCTURED:
        gen_example = (
            "lexigram gen controller users"
            if "web" in features
            else "lexigram gen task nightly_report"
        )
    else:
        gen_example = (
            "lexigram gen controller users"
            if "web" in features
            else "lexigram gen task nightly_report"
        )
    sections = ["```bash", f"cd {project_name}", "pip install -e .", f"{run}", "```"]
    if "web" in features and structure != "minimal":
        sections.append("")
        sections.append("`/` and `/health` are served by the scaffolded controllers.")
    sections += [
        "",
        "## Generators",
        "",
        "The bootstrap is aligned with the canonical generator layout:",
        "",
        "```bash",
        f"{gen_example}",
        "```",
        "",
        "List all generators with `lexigram gen list`.",
        "",
        "## Project layout",
        "",
        "- `application.yaml` — typed configuration (see `lexigram config show`)",
        f"- `src/{package_name}/app.py` — composition root (`create_app`)",
    ]
    if structure == STRUCTURED:
        sections += [
            "- `src/controllers/` — web controllers (auto-discovered)",
            "- `src/models/`, `src/repositories/`, `src/services/` — data layer",
            "- `src/filters/`, `src/interceptors/`, `src/errors/` — web cross-cutting",
        ]
    elif structure == MODULAR:
        sections += [
            (
                f"- `src/{package_name}/modules/` — bounded contexts "
                "(`lexigram new module <name>`)"
            ),
            f"- `src/{package_name}/shared/` — cross-cutting packages",
            f"- `src/{package_name}/infrastructure/` — db/cache/events wiring",
        ]
    else:
        sections += [
            (
                f"- `src/{package_name}/controllers/` — web controllers "
                "(created by `lexigram gen controller users`)"
            ),
            (
                f"- `src/{package_name}/models/`, "
                f"`src/{package_name}/repositories/` — data layer "
                "(created on demand)"
            ),
        ]
    sections += [
        "- `tests/` — boot smoke tests (pytest, asyncio-mode auto)",
        "",
    ]
    return "\n".join(
        [f"# {project_name}\n", f"{spec.description}.\n", "## Quickstart\n", *sections]
    )


def _env_example(project_name: str) -> str:
    return f"""# Lexigram environment overrides (LEX_<SECTION>__<FIELD> syntax).
# Copy to .env and uncomment what you need.

# LEX_APP_NAME={project_name}
# LEX_DEBUG=false
# LEX_ENV=development

# Web server (web.server)
# LEX_WEB__SERVER__HOST=127.0.0.1
# LEX_WEB__SERVER__PORT=8000

# Database URL (sql.backend) — consumed by lexigram-sql
# LEX_SQL__BACKEND__URL=sqlite:///./dev.db

# Auth secret — set a real value before deploying with auth enabled
# LEX_AUTH__SECRET_KEY=change-me-in-production
"""


def _gitignore() -> str:
    return """# Python
__pycache__/
*.py[cod]
.venv/
venv/
dist/
build/
*.egg-info/

# Local environments
.env
.env.local

# Databases / caches / logs
*.db
*.sqlite3
*.log
coverage/
.pytest_cache/
.mypy_cache/
.ruff_cache/
"""


def _sample_module_files(
    package_name: str,
    project_name: str,
) -> dict[str, str]:
    """The modular ``users`` sample bounded context (web templates)."""
    module = "users"
    files = _module_scaffold_files(package_name, module, "UsersModule")
    files[f"src/{package_name}/modules/{module}/controllers/__init__.py"] = (
        _package_line(f"{module}/controllers", ("controller",))
    )
    files[f"src/{package_name}/modules/{module}/controllers/root.py"] = (
        _module_controller(package_name, module)
    )
    return files


def _file_map(
    project_name: str,
    package_name: str,
    template: str,
    structure: str,
) -> dict[str, str]:
    """Return the canonical file map for a project (path → content)."""
    spec = resolve_template(template)
    files = _component_files(package_name, structure)
    files.update(
        {
            f"src/{package_name}/app.py": _app_py(
                project_name, package_name, spec, structure
            ),
            "application.yaml": _application_yaml(project_name, spec),
            "pyproject.toml": _pyproject_toml(
                project_name, package_name, spec, structure
            ),
            "README.md": _readme(project_name, spec, structure, package_name),
            ".env.example": _env_example(project_name),
            ".gitignore": _gitignore(),
            "tests/__init__.py": "",
            "tests/conftest.py": _conftest(project_name, package_name, spec),
            "tests/test_app.py": _test_app(spec, structure),
        }
    )
    if structure == STRUCTURED:
        files.update(
            {
                "src/controllers/__init__.py": _package_line(
                    "controllers", ("controller",)
                ),
                "src/controllers/api.py": _controller_module(project_name),
            }
        )
    elif structure == MODULAR:
        files.update(
            {
                f"src/{package_name}/infrastructure/__init__.py": _infrastructure_py(
                    package_name, spec
                ),
                f"src/{package_name}/modules/__init__.py": _modules_init(
                    package_name,
                    (("users", "UsersModule"),) if "web" in spec.features else (),
                ),
            }
        )
        if "web" in spec.features:
            files.update(_sample_module_files(package_name, project_name))
    return files


def render_project(
    template: str,
    project_name: str,
    target_dir: Path,
    *,
    structure: str = STRUCTURED,
    force: bool = False,
) -> list[Path]:
    """Render a canonical Lexigram project into *target_dir*.

    Args:
        template: Template name (``minimal``, ``api``, ``web-api``,
            ``graphql``, ``worker``, ``full``, ``fullstack``).
        project_name: Project / package name (dashes become underscores).
        target_dir: Destination directory (must be empty unless *force*).
        structure: Project structure (``minimal``, ``structured``,
            ``modular``); defaults to ``structured``.
        force: Allow writing into a non-empty directory.

    Returns:
        The list of created file paths.

    Raises:
        ValueError: Unknown template/structure or non-empty target directory.
    """
    if structure not in STRUCTURES:
        raise ValueError(
            f"Unknown structure {structure!r}. Available: {', '.join(STRUCTURES)}"
        )
    resolve_template(template)
    if target_dir.exists() and any(target_dir.iterdir()) and not force:
        raise ValueError(f"Directory {target_dir} is not empty")

    package_name = project_name.replace("-", "_")
    files = _file_map(project_name, package_name, template, structure)

    created: list[Path] = []
    for relative, content in files.items():
        path = target_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not force:
            continue
        path.write_text(content)
        created.append(path)
    return created


_MODULE_IMPORT_RE = re.compile(
    r"^from (?P<pkg>[\w]+)\.modules\.(?P<slug>[\w-]+) import (?P<name>\w+Module)$",
    re.MULTILINE,
)


def _register_module_in_init(
    modules_init: Path,
    package_name: str,
    module: str,
    class_name: str,
) -> None:
    """Register *module* in the generated ``modules/__init__.py`` registry."""
    existing: dict[str, str] = {}
    for match in _MODULE_IMPORT_RE.finditer(modules_init.read_text()):
        if match.group("pkg") == package_name:
            existing[match.group("slug")] = match.group("name")
    existing[module] = class_name
    names = tuple(sorted(existing.items()))
    modules_init.write_text(_modules_init(package_name, names))


def render_module(module_name: str, target_dir: Path) -> list[Path]:
    """Create a bounded context inside a modular project.

    ``lexigram new module <name>`` writes
    ``src/<app>/modules/<name>/`` with a module boundary
    (``@module``), ``protocols.py``, ``provider.py`` and ``services.py`` and
    registers the module in ``modules/__init__.py`` so the composition root
    picks it up automatically.

    Args:
        module_name: Feature name (validated by the CLI).
        target_dir: Project root (must contain ``pyproject.toml``).

    Returns:
        The list of created file paths.

    Raises:
        ValueError: Not a modular project, or the module already exists.
    """
    from lexigram.cli.layout import MODULAR, read_project_layout

    layout = read_project_layout(target_dir)
    if layout.structure != MODULAR:
        raise ValueError(
            "`lexigram new module` requires a modular project "
            "(set [tool.lexigram] structure = modular)."
        )
    module_slug = module_name.replace("-", "_")
    module_dir = target_dir / "src" / layout.app_package / "modules" / module_slug
    if module_dir.exists() and any(module_dir.iterdir()):
        raise ValueError(f"Module {module_name!r} already exists in {module_dir}")

    class_name = (
        "".join(part.capitalize() for part in re.split(r"[-_]", module_name)) + "Module"
    )
    created: list[Path] = []
    for relative, content in _module_scaffold_files(
        layout.app_package, module_slug, class_name
    ).items():
        path = target_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        created.append(path)

    modules_init = module_dir.parent / "__init__.py"
    if modules_init.exists():
        _register_module_in_init(
            modules_init, layout.app_package, module_slug, class_name
        )
    return created


__all__ = [
    "TEMPLATES",
    "component_packages",
    "render_project",
    "resolve_template",
    "root_output_dirs",
    "structure_names",
    "template_names",
]
