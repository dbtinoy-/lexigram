"""Tests for the three generator-aligned project structures."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
import subprocess
import sys

import pytest
from typer.testing import CliRunner

from lexigram.cli.commands.new import app as new_app
from lexigram.cli.scaffold import render_project

_STRUCTURES = ("minimal", "structured", "modular")
_TEMPLATES = ("api", "web-api", "full")


@pytest.fixture
def runner() -> CliRunner:
    """CLI test runner."""
    return CliRunner()


class TestStructureLayouts:
    """Rendered trees match the canonical map per structure."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """CLI test runner."""
        return CliRunner()

    def test_minimal_has_no_component_packages(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        result = runner.invoke(
            new_app,
            [
                "project",
                "my-min",
                "--template",
                "api",
                "--structure",
                "minimal",
                "--directory",
                str(temp_dir),
            ],
        )
        assert result.exit_code == 0, result.output
        project = temp_dir / "my-min"
        assert (project / "src/my_min/app.py").exists()
        assert not (project / "src/controllers").exists()
        pyproject = (project / "pyproject.toml").read_text()
        assert 'structure = "minimal"' in pyproject

    def test_structured_has_sibling_components(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        result = runner.invoke(
            new_app,
            [
                "project",
                "my-std",
                "--template",
                "web-api",
                "--structure",
                "structured",
                "--directory",
                str(temp_dir),
            ],
        )
        assert result.exit_code == 0, result.output
        project = temp_dir / "my-std"
        assert (project / "src/controllers/api.py").exists()
        assert (project / "src/schema/__init__.py").exists()
        assert (project / "src/vector/collections/__init__.py").exists()
        assert not (project / "src/graphql").exists()
        assert not (project / "src/collections").exists()

    def test_modular_has_modules_shared_infrastructure(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        result = runner.invoke(
            new_app,
            [
                "project",
                "my-mod",
                "--template",
                "web-api",
                "--structure",
                "modular",
                "--directory",
                str(temp_dir),
            ],
        )
        assert result.exit_code == 0, result.output
        project = temp_dir / "my-mod"
        assert (project / "src/my_mod/modules/users/__init__.py").exists()
        assert (project / "src/my_mod/modules/users/controllers/root.py").exists()
        assert (project / "src/my_mod/shared/errors/__init__.py").exists()
        assert (project / "src/my_mod/infrastructure/__init__.py").exists()
        assert not (project / "src/my_mod/shared/controllers").exists()
        pyproject = (project / "pyproject.toml").read_text()
        assert 'structure = "modular"' in pyproject

    def test_invalid_structure_rejected(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        result = runner.invoke(
            new_app,
            [
                "project",
                "my-app",
                "--structure",
                "nope",
                "--directory",
                str(temp_dir),
            ],
        )
        assert result.exit_code == 1
        assert "Structure nope not found" in result.output

    @pytest.mark.parametrize("template", _TEMPLATES)
    @pytest.mark.parametrize("structure", _STRUCTURES)
    def test_scaffolded_projects_pass_ruff(
        self, runner: CliRunner, temp_dir: Path, template: str, structure: str
    ) -> None:
        """Every structure x template combination is lint-clean."""
        result = runner.invoke(
            new_app,
            [
                "project",
                f"proj-{template}-{structure}",
                "--template",
                template,
                "--structure",
                structure,
                "--directory",
                str(temp_dir),
            ],
        )
        assert result.exit_code == 0, result.output

        project_dir = temp_dir / f"proj-{template}-{structure}"
        py_files = list(project_dir.rglob("*.py"))
        assert py_files, "No Python files generated"
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                "--select",
                "E,F,I",
                "--",
                *[str(f) for f in py_files],
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, (
            f"ruff failed for {template}/{structure}:\n{proc.stdout}\n{proc.stderr}"
        )


@pytest.fixture
def modular_project(temp_dir: Path) -> Path:
    """A rendered modular web-api project."""
    render_project(
        "web-api",
        "my-platform",
        Path(temp_dir) / "my-platform",
        structure="modular",
    )
    return Path(temp_dir) / "my-platform"



class TestNewModuleCommand:
    """lexigram new module creates and registers a bounded context."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """CLI test runner."""
        return CliRunner()

    def test_creates_boundary_files(
        self, runner: CliRunner, modular_project: Path
    ) -> None:
        result = runner.invoke(
            new_app, ["module", "auth", "--directory", str(modular_project)]
        )  # noqa: E501
        assert result.exit_code == 0, result.output
        module_dir = modular_project / "src/my_platform/modules/auth"
        for name in ("__init__.py", "protocols.py", "provider.py", "services.py"):
            assert (module_dir / name).exists(), name
        init = (module_dir / "__init__.py").read_text()
        assert "class AuthModule(Module):" in init
        assert "@module()" in init

    def test_registers_module_in_registry(
        self, runner: CliRunner, modular_project: Path
    ) -> None:
        runner.invoke(new_app, ["module", "auth", "--directory", str(modular_project)])
        registry = (
            modular_project / "src/my_platform/modules/__init__.py"
        ).read_text()
        assert "from my_platform.modules.auth import AuthModule" in registry
        assert "    AuthModule," in registry

    def test_rejects_non_modular_project(
        self, runner: CliRunner, temp_dir: Path
    ) -> None:
        render_project(
            "web-api", "my-app", Path(temp_dir) / "my-app", structure="structured"
        )
        result = runner.invoke(
            new_app, ["module", "auth", "--directory", str(temp_dir / "my-app")]
        )
        assert result.exit_code == 1
        assert "requires a modular project" in result.output

    def test_refuses_existing_module(
        self, runner: CliRunner, modular_project: Path
    ) -> None:
        first = runner.invoke(
            new_app, ["module", "billing", "--directory", str(modular_project)]
        )
        assert first.exit_code == 0, first.output
        second = runner.invoke(
            new_app, ["module", "billing", "--directory", str(modular_project)]
        )
        assert second.exit_code == 1
        assert "already exists" in second.output

    def test_registry_imports_and_boots_modules_package(
        self, runner: CliRunner, modular_project: Path
    ) -> None:
        """The module registry imports cleanly against real lexigram APIs."""
        created = runner.invoke(
            new_app, ["module", "auth", "--directory", str(modular_project)]
        )
        assert created.exit_code == 0, created.output
        original = os.getcwd()
        os.chdir(modular_project)
        try:
            sys.path.insert(0, str(modular_project / "src"))
            modules = importlib.import_module("my_platform.modules")
            assert [m.__name__ for m in modules.MODULES] == [
                "AuthModule",
                "UsersModule",
            ]
            auth = importlib.import_module("my_platform.modules.auth")
            assert hasattr(auth, "AuthModule")
        finally:
            sys.path.remove(str(modular_project / "src"))
            os.chdir(original)


class TestGenModuleOption:
    """lexigram gen --module resolves paths against the modular layout."""

    def test_controller_writes_into_module(
        self,
        runner: CliRunner,
        modular_project: Path,
        cli_app_with_web_generators,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(modular_project)
        result = runner.invoke(
            cli_app_with_web_generators,
            ["gen", "controller", "users", "--module", "auth"],
        )
        assert result.exit_code == 0, result.output
        expected = (
            modular_project
            / "src/my_platform/modules/auth/controllers/users_controller.py"
        )
        assert expected.exists(), result.output
        assert "created" in result.output.lower()

    def test_cross_cutting_ignores_module(
        self,
        runner: CliRunner,
        modular_project: Path,
        cli_app_with_core_generators,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(modular_project)
        result = runner.invoke(
            cli_app_with_core_generators,
            ["gen", "provider", "billing", "--module", "auth"],
        )
        assert result.exit_code == 0, result.output
        expected = (
            modular_project / "src/my_platform/shared/providers/billing_provider.py"
        )
        assert expected.exists(), result.output
        assert "created" in result.output.lower()

    def test_module_local_without_module_is_rejected(
        self,
        runner: CliRunner,
        modular_project: Path,
        cli_app_with_web_generators,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(modular_project)
        result = runner.invoke(
            cli_app_with_web_generators, ["gen", "controller", "users"]
        )
        assert result.exit_code in (1, 2)
        assert "module-local" in result.output

    def test_minimal_nests_inside_app_package(
        self,
        runner: CliRunner,
        temp_dir: Path,
        cli_app_with_core_generators,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        render_project(
            "api", "my-app", Path(temp_dir) / "my-app", structure="minimal"
        )
        project = Path(temp_dir) / "my-app"
        monkeypatch.chdir(project)
        result = runner.invoke(
            cli_app_with_core_generators,
            ["gen", "provider", "billing"],
        )
        assert result.exit_code == 0, result.output
        assert (project / "src/my_app/providers/billing_provider.py").exists()

    def test_structured_ignores_module_option(
        self,
        runner: CliRunner,
        temp_dir: Path,
        cli_app_with_web_generators,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        render_project(
            "web-api", "my-app", Path(temp_dir) / "my-app", structure="structured"
        )
        project = Path(temp_dir) / "my-app"
        monkeypatch.chdir(project)
        result = runner.invoke(
            cli_app_with_web_generators,
            ["gen", "controller", "users", "--module", "auth"],
        )
        assert result.exit_code == 0, result.output
        assert (project / "src/controllers/users_controller.py").exists()
