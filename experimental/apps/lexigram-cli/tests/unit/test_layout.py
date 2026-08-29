"""Tests for the canonical generator -> path layout module."""

from __future__ import annotations

from pathlib import Path

import pytest

from lexigram.cli.layout import (
    MINIMAL,
    MODULAR,
    STRUCTURED,
    component_packages,
    read_project_layout,
    resolve_output_dir,
    validate_definition,
)


class TestResolveOutputDir:
    """Structure-aware generator path resolution."""

    def test_structured_passthrough(self) -> None:
        for default in (
            "src/controllers",
            "src/schema/dataloaders",
            "src/vector/collections",
            "migrations/versions",
            "tests/unit",
            "src",
        ):
            assert resolve_output_dir(default, structure=STRUCTURED) == default

    def test_minimal_nests_inside_app_package(self) -> None:
        assert (
            resolve_output_dir(
                "src/controllers", structure=MINIMAL, app_package="my_app"
            )
            == "src/my_app/controllers"
        )
        assert (
            resolve_output_dir(
                "src/vector/collections", structure=MINIMAL, app_package="my_app"
            )
            == "src/my_app/vector/collections"
        )
        assert (
            resolve_output_dir("src", structure=MINIMAL, app_package="my_app")
            == "src/my_app"
        )
        # Root-level dirs stay at the project root.
        assert (
            resolve_output_dir("tests/unit", structure=MINIMAL, app_package="my_app")
            == "tests/unit"
        )
        assert (
            resolve_output_dir(
                "migrations/versions", structure=MINIMAL, app_package="my_app"
            )
            == "migrations/versions"
        )

    def test_modular_shared_layer(self) -> None:
        for default, expected in (
            ("src/errors", "src/my_app/shared/errors"),
            ("src/filters", "src/my_app/shared/filters"),
            ("src/schema", "src/my_app/shared/schema"),
            ("src/schema/dataloaders", "src/my_app/shared/schema/dataloaders"),
            ("src/vector/collections", "src/my_app/shared/vector/collections"),
            ("src/providers", "src/my_app/shared/providers"),
            ("src/storage/backends", "src/my_app/shared/storage/backends"),
        ):
            assert (
                resolve_output_dir(default, structure=MODULAR, app_package="my_app")
                == expected
            )

    def test_modular_module_local_requires_module(self) -> None:
        for default in (
            "src/controllers",
            "src/models",
            "src/services",
            "src/repositories",
            "src/events",
            "src/admin/actions",
        ):
            with pytest.raises(ValueError, match="module-local"):
                resolve_output_dir(default, structure=MODULAR, app_package="my_app")

    def test_modular_module_local_with_module(self) -> None:
        assert (
            resolve_output_dir(
                "src/controllers",
                structure=MODULAR,
                app_package="my_app",
                module="auth",
            )
            == "src/my_app/modules/auth/controllers"
        )
        assert (
            resolve_output_dir(
                "src/admin/resources",
                structure=MODULAR,
                app_package="my_app",
                module="admin",
            )
            == "src/my_app/modules/admin/admin/resources"
        )

    def test_modular_tests_with_module(self) -> None:
        assert (
            resolve_output_dir(
                "tests/unit",
                structure=MODULAR,
                app_package="my_app",
                module="billing",
            )
            == "src/my_app/modules/billing/tests"
        )

    def test_modular_resource_requires_module(self) -> None:
        with pytest.raises(ValueError, match="module-local"):
            resolve_output_dir(
                "src", structure=MODULAR, app_package="my_app", generator="resource"
            )
        assert (
            resolve_output_dir(
                "src",
                structure=MODULAR,
                app_package="my_app",
                generator="resource",
                module="auth",
            )
            == "src/my_app/modules/auth"
        )

    def test_modular_src_root_generators(self) -> None:
        assert (
            resolve_output_dir(
                "src", structure=MODULAR, app_package="my_app", generator="mcp-server"
            )
            == "src/my_app/shared"
        )
        assert (
            resolve_output_dir("src", structure=MINIMAL, app_package="my_app")
            == "src/my_app"
        )

    def test_unknown_output_dir_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown generator output directory"):
            resolve_output_dir(
                "migrations/other", structure=MINIMAL, app_package="my_app"
            )


class TestValidateDefinition:
    """Alignment between generator definitions and the canonical map."""

    def test_aligned_definitions(self) -> None:
        assert validate_definition("controller", "src/controllers") is None
        assert validate_definition("graphql", "src/schema") is None
        assert validate_definition("dataloader", "src/schema/dataloaders") is None
        assert (
            validate_definition("vector_collection", "src/vector/collections")
            is None
        )
        assert validate_definition("migration", "migrations/versions") is None
        assert validate_definition("seeder", "seeds") is None
        assert validate_definition("test", "tests/unit") is None
        assert validate_definition("mcp-server", "src") is None
        assert validate_definition("resource", "src") is None

    def test_drift_is_detected(self) -> None:
        assert validate_definition("controller", "src/schema") is not None
        assert validate_definition("graphql", "src/controllers") is not None
        assert validate_definition("controller", "src") is not None
        assert validate_definition("unknown", "src/nowhere") is not None


class TestReadProjectLayout:
    """Project metadata discovery from pyproject.toml."""

    def test_no_pyproject_returns_structured_default(self, tmp_path: Path) -> None:
        layout = read_project_layout(tmp_path)
        assert layout.structure == STRUCTURED
        assert layout.app_package == "app"
        assert layout.declared is False
        assert layout.structure_declared is False

    def test_reads_structure_and_module(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            "[tool.lexigram]\nstructure = \"modular\"\nmodule = \"my_app.app:app\"\n"
        )
        layout = read_project_layout(tmp_path)
        assert layout.structure == MODULAR
        assert layout.app_package == "my_app"
        assert layout.declared is True
        assert layout.structure_declared is True
        assert layout.module_target() == "my_app.app:app"

    def test_legacy_module_without_structure(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            "[tool.lexigram]\nmodule = \"old_app.app:app\"\n"
        )
        layout = read_project_layout(tmp_path)
        assert layout.structure == STRUCTURED
        assert layout.app_package == "old_app"
        assert layout.structure_declared is False


class TestComponentPackages:
    """Scaffold-facing canonical map helpers."""

    def test_covers_renamed_packages(self) -> None:
        packages = component_packages()
        assert "schema" in packages
        assert "schema/dataloaders" in packages
        assert "vector/collections" in packages
        assert "collections" not in packages
        assert "graphql" not in packages
