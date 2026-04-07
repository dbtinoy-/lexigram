from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lexigram.app.discovery import (
    discover_modules_from_directories,
    discover_modules_from_entry_points,
)
from lexigram.di.module import Module, module


class TestDiscoverModulesFromEntryPoints:
    def test_returns_empty_dict_when_no_entry_points(self) -> None:
        with patch("importlib.metadata.entry_points", return_value=[]):
            result = discover_modules_from_entry_points()
        assert result == {}

    def test_returns_discovered_module_class(self) -> None:
        @module()
        class FakeModule(Module):
            pass

        ep = MagicMock()
        ep.name = "fake"
        ep.load.return_value = FakeModule

        with patch("importlib.metadata.entry_points", return_value=[ep]):
            result = discover_modules_from_entry_points()

        assert "fake" in result
        assert result["fake"] is FakeModule

    def test_skips_non_module_classes(self) -> None:
        ep = MagicMock()
        ep.name = "not_a_module"
        ep.load.return_value = str  # Not a Module subclass

        with patch("importlib.metadata.entry_points", return_value=[ep]):
            result = discover_modules_from_entry_points()

        assert result == {}

    def test_skips_base_module_class_itself(self) -> None:
        ep = MagicMock()
        ep.name = "base"
        ep.load.return_value = Module  # Base class itself should be skipped

        with patch("importlib.metadata.entry_points", return_value=[ep]):
            result = discover_modules_from_entry_points()

        assert result == {}

    def test_skips_failed_load_gracefully(self) -> None:
        ep = MagicMock()
        ep.name = "broken"
        ep.load.side_effect = ImportError("package missing")

        with patch("importlib.metadata.entry_points", return_value=[ep]):
            result = discover_modules_from_entry_points()

        assert result == {}

    def test_custom_group(self) -> None:
        with patch("importlib.metadata.entry_points", return_value=[]) as mock_ep:
            discover_modules_from_entry_points(group="myapp.modules")
        mock_ep.assert_called_once_with(group="myapp.modules")

    def test_default_group_is_lexigram_modules(self) -> None:
        with patch("importlib.metadata.entry_points", return_value=[]) as mock_ep:
            discover_modules_from_entry_points()
        mock_ep.assert_called_once_with(group="lexigram.modules")


class TestDiscoverModulesFromDirectories:
    def test_returns_empty_when_dir_does_not_exist(self, tmp_path: Path) -> None:
        result = discover_modules_from_directories([tmp_path / "nonexistent"])
        assert result == {}

    def test_returns_empty_for_empty_dir(self, tmp_path: Path) -> None:
        result = discover_modules_from_directories([tmp_path])
        assert result == {}

    def test_discovers_module_from_plugin_py(self, tmp_path: Path) -> None:
        plugin_file = tmp_path / "plugin.py"
        plugin_file.write_text(
            "from lexigram.di.module import Module, module\n"
            "\n"
            "@module()\n"
            "class MyModule(Module):\n"
            "    pass\n"
        )
        result = discover_modules_from_directories([tmp_path])
        assert len(result) == 1
        cls = next(iter(result.values()))
        assert issubclass(cls, Module)

    def test_skips_files_with_no_module_subclass(self, tmp_path: Path) -> None:
        (tmp_path / "plugin.py").write_text("x = 1\n")
        result = discover_modules_from_directories([tmp_path])
        assert result == {}

    def test_accepts_string_paths(self, tmp_path: Path) -> None:
        result = discover_modules_from_directories([str(tmp_path)])
        assert result == {}  # empty dir, just verifying no crash

    def test_skips_broken_plugin_file_gracefully(self, tmp_path: Path) -> None:
        (tmp_path / "plugin.py").write_text("this is not valid python !!!")
        result = discover_modules_from_directories([tmp_path])
        assert result == {}  # must not raise
