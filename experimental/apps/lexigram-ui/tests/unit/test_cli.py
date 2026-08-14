"""Tests for the lexigram-ui component CLI — registry and add command."""

from __future__ import annotations

from pathlib import Path

from lexigram.ui.cli.add import _collect_files, _find_ui_package
from lexigram.ui.cli.registry import COMPONENT_REGISTRY, ComponentEntry


class TestComponentEntry:
    """Tests for the ComponentEntry dataclass."""

    def test_entry_creation(self) -> None:
        entry = ComponentEntry(
            name="test",
            description="A test component",
            source_path="lexigram/ui/atoms/test.py",
        )
        assert entry.name == "test"
        assert entry.description == "A test component"
        assert entry.source_path == "lexigram/ui/atoms/test.py"
        assert entry.dependencies == []
        assert entry.requires == []

    def test_entry_with_dependencies(self) -> None:
        entry = ComponentEntry(
            name="button",
            description="Button component",
            source_path="lexigram/ui/atoms/button.py",
            dependencies=["lexigram/ui/core/base.py"],
            requires=["core-ui"],
        )
        assert entry.dependencies == ["lexigram/ui/core/base.py"]
        assert entry.requires == ["core-ui"]


class TestComponentRegistry:
    """Tests for the COMPONENT_REGISTRY dict."""

    def test_registry_has_expected_components(self) -> None:
        expected = {
            "button", "badge", "card", "input", "modal",
            "select", "tabs", "toast", "tooltip", "skeleton",
            "form", "pagination",
        }
        assert set(COMPONENT_REGISTRY) == expected

    def test_every_entry_is_component_entry(self) -> None:
        for entry in COMPONENT_REGISTRY.values():
            assert isinstance(entry, ComponentEntry)

    def test_every_entry_has_name_matching_key(self) -> None:
        for key, entry in COMPONENT_REGISTRY.items():
            assert entry.name == key

    def test_every_entry_has_source_path(self) -> None:
        for entry in COMPONENT_REGISTRY.values():
            assert entry.source_path.startswith("lexigram/ui/")

    def test_button_entry(self) -> None:
        entry = COMPONENT_REGISTRY["button"]
        assert entry.description == "Button component with semantic color variants"
        assert "lexigram/ui/core/base.py" in entry.dependencies

    def test_form_entry_dependencies(self) -> None:
        entry = COMPONENT_REGISTRY["form"]
        assert len(entry.dependencies) == 3
        assert "lexigram/ui/core/base.py" in entry.dependencies
        assert "lexigram/ui/atoms/button.py" in entry.dependencies
        assert "lexigram/ui/molecules/form_field.py" in entry.dependencies


class TestFindUiPackage:
    """Tests for _find_ui_package helper."""

    def test_finds_ui_package(self) -> None:
        pkg_path = _find_ui_package()
        assert pkg_path is not None
        assert pkg_path.exists()
        assert (pkg_path / "lexigram" / "ui" / "cli").exists()
        assert (pkg_path / "lexigram" / "ui" / "core").exists()
        assert (pkg_path / "lexigram" / "ui" / "atoms").exists()


class TestCollectFiles:
    """Tests for _collect_files helper."""

    def test_collect_button_files(self) -> None:
        ui_pkg = _find_ui_package()
        assert ui_pkg is not None
        entry = COMPONENT_REGISTRY["button"]
        files = _collect_files(entry, ui_pkg)
        assert len(files) >= 1
        assert any(f.name == "button.py" for f in files)

    def test_collect_card_files_includes_base(self) -> None:
        ui_pkg = _find_ui_package()
        assert ui_pkg is not None
        entry = COMPONENT_REGISTRY["card"]
        files = _collect_files(entry, ui_pkg)
        assert len(files) >= 1
        assert any(f.name == "card.py" for f in files)
        assert any(f.name == "base.py" for f in files)

    def test_collect_form_files_includes_deps(self) -> None:
        ui_pkg = _find_ui_package()
        assert ui_pkg is not None
        entry = COMPONENT_REGISTRY["form"]
        files = _collect_files(entry, ui_pkg)
        assert len(files) >= 3
        assert any(f.name == "forms.py" for f in files)
        assert any(f.name == "button.py" for f in files)
        assert any(f.name == "form_field.py" for f in files)

    def test_collect_files_returns_distinct_paths(self) -> None:
        ui_pkg = _find_ui_package()
        assert ui_pkg is not None
        for entry in COMPONENT_REGISTRY.values():
            files = _collect_files(entry, ui_pkg)
            assert len(files) == len(set(files)), f"Duplicate files for {entry.name}"

    def test_all_collected_files_exist(self) -> None:
        ui_pkg = _find_ui_package()
        assert ui_pkg is not None
        for entry in COMPONENT_REGISTRY.values():
            files = _collect_files(entry, ui_pkg)
            for f in files:
                assert f.exists(), f"File not found: {f} (component: {entry.name})"


class TestAddCommandEntryPoint:
    """Tests that the Typer app is properly configured."""

    def test_app_is_typer(self) -> None:
        from lexigram.ui.cli.add import app
        assert app.info.name == "add"

    def test_add_unknown_component(self) -> None:
        from typer.testing import CliRunner
        from lexigram.ui.cli.add import app

        runner = CliRunner()
        result = runner.invoke(app, ["nonexistent"])
        assert result.exit_code == 1
        assert "Unknown component" in result.stderr

    def test_add_component_help(self) -> None:
        from typer.testing import CliRunner
        from lexigram.ui.cli.add import app

        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Copy a UI component" in result.stdout
        assert "component_name" in result.stdout

    def test_add_button_component_to_tmp(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from lexigram.ui.cli.add import app

        runner = CliRunner()
        output_dir = str(tmp_path / "ui")
        result = runner.invoke(app, ["button", "--output", output_dir])
        assert result.exit_code == 0, f"STDERR: {result.stdout}"
        assert "Added button component" in result.stdout
        assert (tmp_path / "ui" / "lexigram" / "ui" / "atoms" / "button.py").exists()

    def test_add_card_component_copies_deps(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from lexigram.ui.cli.add import app

        runner = CliRunner()
        output_dir = str(tmp_path / "ui")
        result = runner.invoke(app, ["card", "--output", output_dir])
        assert result.exit_code == 0
        assert (tmp_path / "ui" / "lexigram" / "ui" / "molecules" / "card.py").exists()
        assert (tmp_path / "ui" / "lexigram" / "ui" / "core" / "base.py").exists()

    def test_add_duplicate_skips_without_force(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from lexigram.ui.cli.add import app

        runner = CliRunner()
        output_dir = str(tmp_path / "ui")
        runner.invoke(app, ["button", "--output", output_dir])
        result = runner.invoke(app, ["button", "--output", output_dir])
        assert result.exit_code == 0
        assert "Skipped" in result.stdout
        assert "No files were copied" in result.stdout

    def test_add_duplicate_with_force_overwrites(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from lexigram.ui.cli.add import app

        runner = CliRunner()
        output_dir = str(tmp_path / "ui")
        runner.invoke(app, ["button", "--output", output_dir])
        result = runner.invoke(app, ["button", "--output", output_dir, "--force"])
        assert result.exit_code == 0
        assert "Added button component" in result.stdout
