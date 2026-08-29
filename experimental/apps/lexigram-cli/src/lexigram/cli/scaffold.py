"""Canonical Lexigram project scaffold.

Single source of truth for project bootstrapping:

- ``lexigram new project --template <name>`` (``commands/new.py``)
- ``ProjectBuilder.create_project`` (``registry/template.py``)
- scaffold alignment tests (``tests/unit/test_scaffold_alignment.py``)

Every generated file targets the **real** lexigram APIs (``Application``,
``LexigramConfig``, ``WebModule``, ``Controller``) and the **generator SDK
layout** — the component packages below mirror ``lexigram gen`` output
directories, so a scaffolded project and its generators stay aligned:

    lexigram new project myapp --template web-api
    cd myapp && pip install -e .
    lexigram gen controller users     # writes src/controllers/users_controller.py
    lexigram dev                      # WebModule auto-discovers it

The generated ``application.yaml`` is validated by :class:`LexigramConfig`
(extra sections such as ``web`` / ``sql`` are consumed through the
``lexigram.config`` entry-point registry), and ``create_app()`` is a
standard composition root: bootable via ``lexigram dev`` / ``lexigram run``
and directly in pytest fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import textwrap

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


# Each component package mirrors a lexigram gen output directory.  Keys are
# paths relative to the project ``src/`` directory.  The values are the
# generator names that emit into that package (informational — tests keep
# this in sync with the contributor registry).
_COMPONENTS: dict[str, tuple[str, ...]] = {
    "admin/actions": ("admin_action",),
    "admin/resources": ("admin_resource",),
    "audit": ("audited",),
    "clients": ("api_client",),
    "collections": ("vector_collection",),
    "commands": ("command",),
    "consumers": ("message_consumer",),
    "controllers": ("controller",),
    "errors": ("error",),
    "events": ("event",),
    "features": ("feature_flag",),
    "filters": ("exception_filter", "filter"),
    "graphql": ("graphql",),
    "graphql/dataloaders": ("dataloader",),
    "guards": ("auth_guard", "guard"),
    "handlers": ("event_handler",),
    "health": ("health",),
    "interceptors": ("interceptor",),
    "mcp": ("mcp-controller", "mcp-server"),
    "metrics": ("metric",),
    "middleware": ("middleware",),
    "models": ("model",),
    "notifications": ("notification_template",),
    "pipelines": ("pipeline",),
    "policies": ("auth_policy",),
    "projections": ("projection",),
    "providers": ("provider",),
    "queries": ("query",),
    "repositories": ("cache_repo", "document_repo", "repository"),
    "sagas": ("saga", "saga_step"),
    "search": ("search_index",),
    "services": ("service",),
    "storage/backends": ("storage_driver",),
    "tasks": ("task",),
    "tenancy": ("tenant_resolver",),
    "webhooks": ("webhook",),
    "websocket": ("websocket",),
    "workflows": ("workflow_def",),
}

# Root-level output directories of the generator SDK.
_ROOT_DIRS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("migrations/versions", ("migration",)),
    ("seeds", ("seeder",)),
    ("tests/unit", ("test",)),
)


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


def resolve_template(name: str) -> ProjectTemplateSpec:
    """Resolve a template name (following aliases)."""
    spec = TEMPLATES.get(TEMPLATE_ALIASES.get(name, name))
    if spec is None:
        raise ValueError(
            f"Unknown template {name!r}. Available: {', '.join(template_names())}"
        )
    return spec


def component_packages() -> dict[str, tuple[str, ...]]:
    """Return the src-relative component package map (copy)."""
    return dict(_COMPONENTS)


def root_output_dirs() -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Return generator root output directories (copy)."""
    return _ROOT_DIRS


def _package_line(package: str, generators: tuple[str, ...]) -> str:
    names = ", ".join(generators)
    return f'"""{package} package.\n\nWriters: {names} (lexigram gen)."""\n'


# Top-level component packages that shadow standard-library / site-package
# names.  They are created only when `lexigram gen` actually writes into them
# (the user explicitly opted in) — pre-creating them would break imports:
#   - ``src/collections`` shadows the stdlib ``collections`` package
#   - ``src/graphql`` shadows the ``graphql`` (graphql-core) package used by
#     strawberry, which backs the GraphQL framework integration
_SHADOWED_TOP_LEVEL_NAMES = {"collections", "graphql"}


def _component_files(package_name: str) -> dict[str, str]:
    """Component ``__init__.py`` files for the canonical layout."""
    files: dict[str, str] = {}
    for package, generators in _COMPONENTS.items():
        top = package.split("/")[0]
        if top in _SHADOWED_TOP_LEVEL_NAMES:
            continue
        files[f"src/{package}/__init__.py"] = _package_line(package, generators)
    for package, generators in _ROOT_DIRS:
        files[f"{package}/__init__.py"] = _package_line(package, generators)
    files[f"src/{package_name}/__init__.py"] = f'"""{package_name} package."""\n'
    files[f"src/{package_name}/py.typed"] = ""
    return files


def _application_yaml(project_name: str, spec: ProjectTemplateSpec) -> str:
    features = spec.features
    lines = [
        "# Lexigram configuration — validated by LexigramConfig plus the",
        "# `lexigram.config` entry-point models (web → WebConfig, sql → DatabaseConfig).",
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


def _wheel_packages(package_name: str) -> list[str]:
    """Wheel packages: the app package plus every top-level component package."""
    packages = {f"src/{package_name}"}
    for relative in _COMPONENTS:
        packages.add(f"src/{relative.split('/')[0]}")
    return sorted(packages)


def _pyproject_toml(project_name: str, package_name: str, spec: ProjectTemplateSpec) -> str:
    deps = "".join(f'    "{dep}",\n' for dep in spec.dependencies)
    wheel = "".join(f'    "{pkg}",\n' for pkg in _wheel_packages(package_name))
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


def _module_instances(
    features: frozenset[str], project_name: str
) -> list[tuple[str, list[str]]]:
    """Ordered ``(comment, configure-call lines)`` pairs for the composition root.

    The web module is appended last so the server boots after every
    dependency is registered.
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
    if "graphql" in features:
        calls.append(
            (
                "# GraphQL - reads the `graphql:` section.",
                ["GraphQLModule.configure()"],
            )
        )
    if "web" in features:
        calls.append(
            (
                "# Web server - controllers written by `lexigram gen controller` are",
                ['WebModule.configure(discover=["controllers"])'],
            )
        )
    return calls


def _app_py(project_name: str, package_name: str, spec: ProjectTemplateSpec) -> str:
    features = spec.features
    module_imports = _module_imports(features)
    module_imports.extend(
        [
            "from lexigram.app import Application",
            "from lexigram.config import LexigramConfig",
        ]
    )
    module_imports.sort()

    module_lines = ["    application.add_modules(", "        ["]
    for comment, call_lines in _module_instances(features, project_name):
        module_lines.append(f"            # {comment.lstrip('#').strip()}")
        for index, line in enumerate(call_lines):
            if index == len(call_lines) - 1 and not line.rstrip().endswith(","):
                line = f"{line},"
            module_lines.append(f"            {line}")
    module_lines.append("        ]")
    module_lines.append("    )")
    notes = "\n".join(
        "\n".join(textwrap.wrap(note, width=88)) for note in spec.notes
    )
    return f'''"""{project_name} - composition root.

{notes}
"""
from __future__ import annotations

{chr(10).join(module_imports)}


def create_app(config: "LexigramConfig | None" = None) -> "Application":
    """Create the application in ``CREATED`` state (not yet started).

    Args:
        config: Optional pre-loaded config.  When ``None`` the framework
            auto-discovers ``application.yaml`` from the working directory.

    Returns:
        The bootable application instance.
    """
    application = Application(name="{project_name}", config=config)
{chr(10).join(module_lines)}
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


def _test_app(spec: ProjectTemplateSpec) -> str:
    if "web" in spec.features:
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


def _readme(project_name: str, spec: ProjectTemplateSpec) -> str:
    features = spec.features
    run = "lexigram dev" if "web" in features else "pytest"
    gen_example = (
        "lexigram gen controller users"
        if "web" in features
        else "lexigram gen task nightly_report"
    )
    sections = ["```bash", f"cd {project_name}", "pip install -e .", f"{run}", "```"]
    if "web" in features:
        sections.append("")
        sections.append("`/health` is served by the scaffolded `ApiController`.")
    sections += [
        "",
        "## Generators",
        "",
        "The bootstrap already contains every package `lexigram gen` writes into:",
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
        f"- `src/{project_name}/app.py` — composition root (`create_app`)",
        "- `src/controllers/` — web controllers (auto-discovered)",
        "- `src/models/`, `src/repositories/`, `src/services/` — data layer",
        "- `src/filters/`, `src/interceptors/`, `src/errors/` — web cross-cutting",
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


def _file_map(
    project_name: str,
    package_name: str,
    template: str,
) -> dict[str, str]:
    """Return the canonical file map for a project (path → content)."""
    spec = resolve_template(template)
    files = _component_files(package_name)
    files.update(
        {
            f"src/{package_name}/app.py": _app_py(project_name, package_name, spec),
            "src/controllers/__init__.py": _package_line(
                "controllers", ("controller",)
            ),
            "src/controllers/api.py": _controller_module(project_name),
            "application.yaml": _application_yaml(project_name, spec),
            "pyproject.toml": _pyproject_toml(project_name, package_name, spec),
            "README.md": _readme(project_name, spec),
            ".env.example": _env_example(project_name),
            ".gitignore": _gitignore(),
            "tests/__init__.py": "",
            "tests/conftest.py": _conftest(project_name, package_name, spec),
            "tests/test_app.py": _test_app(spec),
        }
    )
    return files


def render_project(
    template: str,
    project_name: str,
    target_dir: Path,
    *,
    force: bool = False,
) -> list[Path]:
    """Render a canonical Lexigram project into *target_dir*.

    Args:
        template: Template name (``minimal``, ``api``, ``web-api``,
            ``graphql``, ``worker``, ``full``, ``fullstack``).
        project_name: Project / package name (dashes become underscores).
        target_dir: Destination directory (must be empty unless *force*).
        force: Allow writing into a non-empty directory.

    Returns:
        The list of created file paths.

    Raises:
        ValueError: Unknown template or non-empty target directory.
    """
    spec = resolve_template(template)
    if target_dir.exists() and any(target_dir.iterdir()) and not force:
        raise ValueError(f"Directory {target_dir} is not empty")

    package_name = project_name.replace("-", "_")
    files = _file_map(project_name, package_name, template)

    created: list[Path] = []
    for relative, content in files.items():
        path = target_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not force:
            continue
        path.write_text(content)
        created.append(path)
    return created


__all__ = [
    "TEMPLATES",
    "component_packages",
    "render_project",
    "resolve_template",
    "root_output_dirs",
    "template_names",
]
