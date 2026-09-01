"""Canonical generator -> project-path map for every project structure.

Single source of truth shared by:

- ``lexigram new project`` scaffolding (which component packages exist)
- ``lexigram gen`` (where a generator writes inside the current project)
- the alignment gate (``dev/checks/generator_output.py``)

Three first-class structures are supported:

- ``minimal`` — single package ``src/<app>/``; generators write *inside*
  that package (``src/<app>/<component>/...``).
- ``structured`` — generator-native layout: ``src/<app>/`` composition root
  plus sibling component packages at ``src/`` (default).
- ``modular`` — bounded contexts at ``src/<app>/modules/<feature>/``,
  cross-cutting packages at ``src/<app>/shared/`` and shared infrastructure
  wiring at ``src/<app>/infrastructure/``.

The structured path for every component is exactly the ``default_output_dir``
declared by the generator contributors, so scaffolding and code generation
can never drift apart.  The alignment gate validates that guarantee.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ImportError:  # pragma: no cover - Python < 3.11
    import tomli as tomllib  # type: ignore[no-redef]

MINIMAL = "minimal"
STRUCTURED = "structured"
MODULAR = "modular"
STRUCTURES: tuple[str, ...] = (MINIMAL, STRUCTURED, MODULAR)
DEFAULT_STRUCTURE = STRUCTURED


@dataclass(frozen=True)
class ComponentDir:
    """One component package and the generators that write into it.

    Attributes:
        structured: Path under ``src/`` in the structured layout (equals the
            generator contributors' ``default_output_dir`` suffix).
        modular: Same suffix used under ``modules/<feature>/`` or ``shared/``.
        shared: True when the component is cross-cutting (lives in the
            modular ``shared/`` layer instead of inside one feature module).
        generators: Generator names that emit into this package.
    """

    structured: str
    modular: str
    shared: bool
    generators: tuple[str, ...]


# The canonical map.  Keys mirror ``lexigram gen`` defaults exactly.
COMPONENTS: tuple[ComponentDir, ...] = (
    ComponentDir("admin/actions", "admin/actions", False, ("admin_action",)),
    ComponentDir("admin/resources", "admin/resources", False, ("admin_resource",)),
    ComponentDir("audit", "audit", True, ("audited",)),
    ComponentDir("clients", "clients", False, ("api_client",)),
    ComponentDir("commands", "commands", False, ("command",)),
    ComponentDir("consumers", "consumers", False, ("message_consumer",)),
    ComponentDir("controllers", "controllers", False, ("controller",)),
    ComponentDir("errors", "errors", True, ("error",)),
    ComponentDir("events", "events", False, ("event",)),
    ComponentDir("features", "features", True, ("feature_flag",)),
    ComponentDir("filters", "filters", True, ("exception_filter", "filter")),
    ComponentDir("guards", "guards", False, ("auth_guard", "guard")),
    ComponentDir("handlers", "handlers", False, ("event_handler",)),
    ComponentDir("health", "health", True, ("health",)),
    ComponentDir("interceptors", "interceptors", True, ("interceptor",)),
    ComponentDir("mcp", "mcp", True, ("mcp-controller",)),
    ComponentDir("metrics", "metrics", True, ("metric",)),
    ComponentDir("middleware", "middleware", True, ("middleware",)),
    ComponentDir("models", "models", False, ("model",)),
    ComponentDir("notifications", "notifications", False, ("notification_template",)),
    ComponentDir("pipelines", "pipelines", False, ("pipeline",)),
    ComponentDir("policies", "policies", False, ("auth_policy",)),
    ComponentDir("projections", "projections", False, ("projection",)),
    ComponentDir("providers", "providers", True, ("provider",)),
    ComponentDir("queries", "queries", False, ("query",)),
    ComponentDir(
        "repositories",
        "repositories",
        False,
        ("cache_repo", "document_repo", "repository"),
    ),
    ComponentDir("sagas", "sagas", False, ("saga", "saga_step")),
    ComponentDir("schema", "schema", True, ("graphql",)),
    ComponentDir("schema/dataloaders", "schema/dataloaders", True, ("dataloader",)),
    ComponentDir("search", "search", True, ("search_index",)),
    ComponentDir("services", "services", False, ("service",)),
    ComponentDir("storage/backends", "storage/backends", True, ("storage_driver",)),
    ComponentDir("tasks", "tasks", False, ("task",)),
    ComponentDir("tenancy", "tenancy", True, ("tenant_resolver",)),
    ComponentDir(
        "vector/collections", "vector/collections", True, ("vector_collection",)
    ),
    ComponentDir("webhooks", "webhooks", False, ("webhook",)),
    ComponentDir("websocket", "websocket", False, ("websocket",)),
    ComponentDir("workflows", "workflows", False, ("workflow_def",)),
)

# Root-level output directories of the generator SDK (no ``src/`` prefix).
ROOT_DIRS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("migrations/versions", ("migration",)),
    ("seeds", ("seeder",)),
    ("tests/unit", ("test",)),
)

# Generators that emit a single module at the project ``src`` root.
SRC_ROOT_GENERATORS: frozenset[str] = frozenset({"mcp-server"})

# ``resource`` declares ``src`` but writes into ``<dir>/controllers`` (it
# delegates to the controller generator), so it is module-local everywhere.
_RESOURCE_OUTPUT = "resource"

_COMPONENTS_BY_PATH: dict[str, ComponentDir] = {
    component.structured: component for component in COMPONENTS
}
_COMPONENTS_BY_GENERATOR: dict[str, ComponentDir] = {
    generator: component
    for component in COMPONENTS
    for generator in component.generators
}
_ROOTS_BY_PATH: dict[str, tuple[str, ...]] = dict(ROOT_DIRS)
_ROOTS_BY_GENERATOR: dict[str, str] = {
    generator: path for path, generators in ROOT_DIRS for generator in generators
}


@dataclass(frozen=True)
class ProjectLayout:
    """Project layout metadata read from ``[tool.lexigram]``."""

    structure: str = DEFAULT_STRUCTURE
    app_package: str = "app"
    declared: bool = False
    structure_declared: bool = False

    def module_target(self) -> str:
        """Return the default ``[tool.lexigram] module`` target."""
        return f"{self.app_package}.app:app"


def read_project_layout(cwd: Path | None = None) -> ProjectLayout:
    """Read ``[tool.lexigram]`` from ``pyproject.toml`` in *cwd*.

    Falls back to the structured default when no project metadata exists
    (``declared=False``).  ``app_package`` is derived from ``module``
    (``"my_app.app:app"`` -> ``"my_app"``).
    """
    root = Path(cwd or Path.cwd())
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return ProjectLayout()
    try:
        data = tomllib.loads(pyproject.read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return ProjectLayout()
    tool = data.get("tool", {})
    if not isinstance(tool, dict):
        return ProjectLayout()
    lexigram_tool = tool.get("lexigram", {})
    if not isinstance(lexigram_tool, dict):
        return ProjectLayout()

    structure = lexigram_tool.get("structure", DEFAULT_STRUCTURE)
    if structure not in STRUCTURES:
        structure = DEFAULT_STRUCTURE

    module_target = lexigram_tool.get("module", "")
    app_package = "app"
    if isinstance(module_target, str) and module_target.strip():
        raw_package = module_target.split(":")[0].split(".")[0]
        if raw_package:
            app_package = raw_package

    return ProjectLayout(
        structure=structure,
        app_package=app_package,
        declared=bool(lexigram_tool),
        structure_declared="structure" in lexigram_tool,
    )


def component_metadata(output_dir: str) -> ComponentDir | None:
    """Return the component metadata for a ``src/``-relative output dir.

    ``"src"`` and root directories return ``None``; callers should treat the
    ``src``-root case through :data:`SRC_ROOT_GENERATORS`.
    """
    return _COMPONENTS_BY_PATH.get(_strip_src(output_dir) or "")


def generator_component(generator: str) -> ComponentDir | None:
    """Return the component a generator writes into, or ``None``."""
    return _COMPONENTS_BY_GENERATOR.get(generator)


def generator_root_output(generator: str) -> str | None:
    """Return the root output path (``migrations/versions`` etc.) or None."""
    return _ROOTS_BY_GENERATOR.get(generator)


def resolve_output_dir(
    default_output_dir: str,
    *,
    structure: str = DEFAULT_STRUCTURE,
    app_package: str = "app",
    module: str | None = None,
    generator: str | None = None,
) -> str:
    """Map a generator's default output dir onto the active structure.

    Args:
        default_output_dir: The contributor-declared default (``src/...``,
            ``migrations/versions``, ``seeds``, ``tests/unit`` or ``src``).
        structure: One of :data:`STRUCTURES`.
        app_package: The application package (``my_app``).
        module: Optional feature module name (modular structure only).
        generator: Optional generator name — needed for the two ``src``-root
            generators whose real target differs from their declared default
            (``resource`` writes into ``<dir>/controllers``).

    Returns:
        The structure-relative output path.

    Raises:
        ValueError: ``module``-local generator used without ``--module`` in
            the modular structure, or an unknown output directory.
    """
    if structure == STRUCTURED:
        return default_output_dir

    if default_output_dir == "src":
        if generator == _RESOURCE_OUTPUT:
            # Delegates to the controller generator: <dir>/controllers.
            component = _COMPONENTS_BY_PATH["controllers"]
            if structure == MINIMAL:
                return f"src/{app_package}"
            if module is None:
                raise ValueError(
                    "'resource' is module-local in the modular structure; "
                    "re-run with --module <feature>."
                )
            return f"src/{app_package}/modules/{module}"
        if structure == MINIMAL:
            return f"src/{app_package}"
        return f"src/{app_package}/shared"

    if _looks_like_src(default_output_dir):
        suffix = _strip_src(default_output_dir)  # "" for "src"
        if structure == MINIMAL:
            target = f"src/{app_package}"
            return f"{target}/{suffix}" if suffix else target
        # modular
        matched_component: ComponentDir | None = _COMPONENTS_BY_PATH.get(suffix)
        if matched_component is not None and not matched_component.shared and module is None:
            raise ValueError(
                f"'{suffix}' is module-local in the modular structure; "
                "re-run with --module <feature> (or pick src/<app>/shared "
                "for cross-cutting generators)."
            )
        if matched_component is not None and matched_component.shared:
            return f"src/{app_package}/shared/{suffix}"
        if module is None:
            return f"src/{app_package}/shared/{suffix}"
        return f"src/{app_package}/modules/{module}/{suffix}"

    if default_output_dir in _ROOTS_BY_PATH:
        if default_output_dir == "tests/unit" and module is not None:
            return f"src/{app_package}/modules/{module}/tests"
        return default_output_dir

    raise ValueError(f"Unknown generator output directory: {default_output_dir}")


def validate_definition(name: str, default_output_dir: str) -> str | None:
    """Return an error message when a generator definition drifts from the map.

    Returns ``None`` when *name*/*default_output_dir* are aligned with the
    canonical layout (component packages, root dirs, or the two ``src``-root
    generators).
    """
    if default_output_dir == "src":
        if name not in SRC_ROOT_GENERATORS and name != _RESOURCE_OUTPUT:
            return (
                f"{name!r} writes to the package root 'src' but is not a "
                "declared src-root generator"
            )
        if name == _RESOURCE_OUTPUT:
            # The resource generator delegates to controllers; accept both
            # its declared 'src' default and the concrete component path.
            return None
        return None

    component = _COMPONENTS_BY_PATH.get(_strip_src(default_output_dir) or "")
    if component is not None:
        if name not in component.generators:
            return (
                f"{name!r} writes to 'src/{component.structured}' but that "
                f"package is owned by {', '.join(component.generators)}"
            )
        return None

    root_generators = _ROOTS_BY_PATH.get(default_output_dir)
    if root_generators is None:
        return f"{name!r} writes to unknown directory {default_output_dir!r}"
    if name not in root_generators:
        return (
            f"{name!r} writes to '{default_output_dir}' but that directory "
            f"is owned by {', '.join(root_generators)}"
        )
    return None


def component_packages() -> dict[str, tuple[str, ...]]:
    """Return ``{structured path: generators}`` for scaffolding (copy)."""
    return {component.structured: component.generators for component in COMPONENTS}


def root_output_dirs() -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Return the root generator output directories (copy)."""
    return ROOT_DIRS


def _looks_like_src(output_dir: str) -> bool:
    return output_dir == "src" or output_dir.startswith("src/")


def _strip_src(output_dir: str) -> str:
    if output_dir == "src":
        return ""
    if output_dir.startswith("src/"):
        return output_dir[len("src/") :]
    return output_dir


__all__ = [
    "COMPONENTS",
    "DEFAULT_STRUCTURE",
    "MINIMAL",
    "MODULAR",
    "ROOT_DIRS",
    "SRC_ROOT_GENERATORS",
    "STRUCTURED",
    "STRUCTURES",
    "ComponentDir",
    "ProjectLayout",
    "component_metadata",
    "component_packages",
    "generator_component",
    "generator_root_output",
    "read_project_layout",
    "resolve_output_dir",
    "root_output_dirs",
    "validate_definition",
]
