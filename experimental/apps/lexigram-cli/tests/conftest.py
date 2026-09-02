"""Test configuration for lexigram-cli."""

from __future__ import annotations

from collections.abc import Generator
import importlib
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

import pytest
import typer

from lexigram.cli.contributors.core import CoreCliContributor
from lexigram.contracts.cli.protocols import CliContributorProtocol


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Resolve the monorepo root from this test file's location."""
    return Path(__file__).resolve().parent.parent.parent


def _reload_cli_modules_with_contributors(
    contributors: list[CliContributorProtocol],
) -> tuple[object, object]:
    from lexigram.cli.contributors.runtime import ContributorRuntime

    runtime = ContributorRuntime()
    runtime.contributors = list(contributors)

    from lexigram.cli.commands import gen as gen_module
    from lexigram.cli.runtime import main as main_module

    with patch.object(
        ContributorRuntime,
        "from_entry_points",
        return_value=runtime,
    ):
        reloaded_gen = importlib.reload(gen_module)
        reloaded_main = importlib.reload(main_module)
    return reloaded_gen, reloaded_main


@pytest.fixture
def gen_app_with_core_generators() -> Generator[typer.Typer, None, None]:
    """Reload the gen module with explicit core contributor discovery."""
    gen_module, main_module = _reload_cli_modules_with_contributors(
        [CoreCliContributor()]
    )
    try:
        yield gen_module.app
    finally:
        importlib.reload(gen_module)
        importlib.reload(main_module)


@pytest.fixture
def cli_app_with_core_generators() -> Generator[typer.Typer, None, None]:
    """Reload the full CLI app with explicit core contributor discovery."""
    gen_module, main_module = _reload_cli_modules_with_contributors(
        [CoreCliContributor()]
    )
    try:
        yield main_module.app
    finally:
        importlib.reload(gen_module)
        importlib.reload(main_module)


@pytest.fixture
def gen_app_with_web_generators() -> Generator[typer.Typer, None, None]:
    """Reload the gen module with explicit core+web contributor discovery."""
    from lexigram.web.cli.contributor import WebCliContributor

    gen_module, main_module = _reload_cli_modules_with_contributors(
        [CoreCliContributor(), WebCliContributor()]
    )
    try:
        yield gen_module.app
    finally:
        importlib.reload(gen_module)
        importlib.reload(main_module)


@pytest.fixture
def cli_app_with_web_generators() -> Generator[typer.Typer, None, None]:
    """Reload the full CLI app with explicit core+web contributor discovery."""
    from lexigram.web.cli.contributor import WebCliContributor

    gen_module, main_module = _reload_cli_modules_with_contributors(
        [CoreCliContributor(), WebCliContributor()]
    )
    try:
        yield main_module.app
    finally:
        importlib.reload(gen_module)
        importlib.reload(main_module)


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_project(temp_dir: Path) -> Generator[Path, None, None]:
    """Create a temporary project directory in the one project layout.

    Everything lives under the application package ``src/test_project/``:
    feature components at the package root until a node joins a module,
    cross-cutting ones under ``shared/``. The package name is declared the
    only way a project declares it -- through ``[tool.lexigram] module``.
    """
    project_dir = temp_dir / "test_project"
    project_dir.mkdir()

    package_dir = project_dir / "src" / "test_project"
    for component in ("models", "controllers", "services"):
        (package_dir / component).mkdir(parents=True)

    # Create basic pyproject.toml
    pyproject_content = """
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "test-project"
version = "0.1.0"
dependencies = []

[tool.lexigram]
framework_version = "0.1.0"
module = "test_project.app:app"
"""
    (project_dir / "pyproject.toml").write_text(pyproject_content.strip())

    # Create basic application.yaml (empty)
    lexigram_content = """
# Lexigram configuration
"""
    (project_dir / "application.yaml").write_text(lexigram_content.strip())

    # Change to project directory
    original_cwd = Path.cwd()
    os.chdir(project_dir)
    try:
        yield project_dir
    finally:
        os.chdir(original_cwd)


@pytest.fixture
def mock_console_output():
    """Mock console output for testing."""
    from unittest.mock import patch

    from lexigram.cli.lib.console import console

    with patch.object(console, "print") as mock_print:
        yield mock_print
