"""Root conftest.py — shared test fixtures for the Lexigram workspace."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Generator

# ─── Workspace src path injection ───────────────────────────────────────────
# When running with the system Python (not the uv venv), only a subset of
# workspace packages are on sys.path (from editable installs in site-packages).
# This block ensures ALL workspace src/ directories are on sys.path before any
# package-level conftest.py files (and their imports) are processed.
import pkgutil
import sys

_ROOT = Path(__file__).parent
_EXCLUDED = {".venv", "build", "dist", "example", "__pycache__"}
for _src in (
    sorted(_ROOT.glob("*/src"))
    + sorted(_ROOT.glob("*/*/src"))
    + sorted(_ROOT.glob("*/*/*/src"))
):
    if not any(p in _EXCLUDED for p in _src.parts):
        _src_str = str(_src)
        if _src_str not in sys.path:
            sys.path.insert(0, _src_str)
# Also add special test helpers paths
for _extra in [
    _ROOT / "experimental" / "ai" / "lexigram-ai-memory" / "tests" / "unit",
    # Sibling support modules imported by bare name from tests running under
    # --import-mode=importlib (root-level runs do not insert per-file dirs).
    _ROOT / "packages" / "lexigram-web" / "tests" / "unit" / "security",
    _ROOT / "experimental" / "ai" / "lexigram-ai-agents" / "tests" / "unit",
    _ROOT / "experimental" / "ai" / "lexigram-ai" / "tests" / "unit",
    _ROOT / "experimental" / "ai" / "lexigram-ai-rag" / "tests" / "unit",
    # Admin app root so its `from tests.<subdir> import ...` namespace imports
    # resolve when the suite runs from the monorepo root.
    _ROOT / "experimental" / "apps" / "lexigram-admin",
]:
    _extra_str = str(_extra)
    if _extra.exists() and _extra_str not in sys.path:
        sys.path.insert(0, _extra_str)

# Re-extend namespace package __path__ now that all src dirs are on sys.path.
# This is necessary because namespace packages (lexigram, lexigram.ai) may have
# been imported earlier (via .pth editable installs) with a limited sys.path,
# freezing their __path__ before our workspace packages were added.
# We also explicitly import these packages here to force them to be cached correctly
# in sys.modules BEFORE sub-conftest files (e.g. lexigram/tests/conftest.py) run.
from typing import TYPE_CHECKING, Any

import lexigram as _lx  # noqa: E402 — must run after sys.path injection
import lexigram.contracts as _lx_contracts  # noqa: E402

_pkg_imports: list[tuple[str, Any]] = [
    ("lexigram", _lx),
    ("lexigram.contracts", _lx_contracts),
]
try:
    import lexigram.ai as _lx_ai  # noqa: E402

    _pkg_imports.append(("lexigram.ai", _lx_ai))
except ImportError:
    pass  # lexigram-ai is an experimental package; absent from the public mirror

for _ns, _pkg in _pkg_imports:
    if hasattr(_pkg, "__path__"):
        _pkg.__path__ = pkgutil.extend_path(list(_pkg.__path__), _ns)
# ────────────────────────────────────────────────────────────────────────────

import pytest

# Register integration infrastructure fixtures globally so they are available
# in both the root tests/integration/ scenarios and all per-package
# integration test directories. Must be declared here (root conftest) — not in
# sub-package conftests — to avoid "Plugin already registered" errors when
# pytest collects multiple packages in a single run.
pytest_plugins = ["lexigram.testing.integration.fixtures", "pytest_asyncio"]


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest to handle conftest.py module name conflicts in monorepos.

    For monorepos with multiple packages, each having their own tests/ directory,
    pytest would normally try to register all conftest.py files as 'tests.conftest',
    causing "Plugin already registered under a different name" errors.

    With __init__.py files in each tests/ directory and testpaths configured,
    pytest should properly isolate each conftest.py module.
    """
    # Hook to allow early pytest configuration
    # The presence of testpaths in pyproject.toml ensures pytest only searches
    # in specified test directories, preventing global discovery conflicts


def _explicitly_requests_integration(config: pytest.Config) -> bool:
    """Return ``True`` when the user explicitly asked for integration tests.

    The default ``pytest`` invocation runs the unit surface only. Integration
    tests are included when the caller opts in via a ``-m``/``-k`` expression
    (the user is explicitly controlling selection) or by naming an integration
    path on the command line (e.g. ``pytest tests/integration/...``).
    """
    # ``config.invocation_params.args`` is the raw CLI argument tuple. A path
    # named on the command line is checked against ``config.args`` so we can
    # distinguish an explicit path from pytest's default ``testpaths``.
    invocation = list(config.invocation_params.args)

    if any(arg in ("-m", "--markexpr", "-k", "--keyword") for arg in invocation):
        return True

    invocation_paths = {
        str(arg).replace("\\", "/").rstrip("/") for arg in invocation
    }
    for candidate in config.args:
        path = str(candidate).replace("\\", "/").rstrip("/")
        if path not in invocation_paths:
            continue
        if (
            path == "tests/integration"
            or path.startswith("tests/integration/")
            or path.endswith("/integration")
            or "/integration/" in path
        ):
            return True
    return False


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Deselect integration tests unless the user explicitly opted in."""
    if _explicitly_requests_integration(config):
        return

    deselected = [
        item for item in items if item.get_closest_marker("integration") is not None
    ]
    if not deselected:
        return

    items[:] = [item for item in items if item not in deselected]
    config.hook.pytest_deselected(items=deselected)


def pytest_load_initial_conftests(
    early_config: pytest.Config,
    parser: pytest.Parser,
    args: list[str],
) -> None:
    """Handle conftest module loading for monorepo with __init__.py in tests dirs."""
    # This hook runs before conftest files are loaded
    # testpaths configuration prevents the initial conflicts


@pytest.fixture
def anyio_backend() -> str:
    """Configure anyio to use asyncio by default for all tests."""
    return "asyncio"


@pytest.fixture
def setup_container_context() -> Generator[Any, None, None]:
    """Set up container in Context for tests.

    This fixture ensures that get_container() works in tests by setting
    a default container in the Context.

    Usage in tests:
        def test_something(setup_container_context):
            container = setup_container_context
            # use container...

    Note: Not autouse=True because:
    - Tests that don't need DI should not get a container
    - Explicit dependencies make tests clearer
    - Improves test performance for tests that don't need DI
    """
    from lexigram.di import Container
    from lexigram.primitives.context import Context

    # Create a test container and set it in context
    container = Container()
    token = Context.set("container", container)
    yield container
    # Clean up
    Context.reset("container", token)
