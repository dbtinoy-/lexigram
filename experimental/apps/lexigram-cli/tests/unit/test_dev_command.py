"""Tests for lexigram dev command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from lexigram.cli.commands.dev import app


class TestDevCommand:
    def setup_method(self):
        self.runner = CliRunner()

    def test_dev_help(self):
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Start development server" in result.output

    def test_dev_no_entry_point_no_config(self, tmp_path):
        result = self.runner.invoke(app, [])
        # Should fail because no entry point found in empty dir
        assert result.exit_code == 1
        assert "Could not find application entry point" in result.output

    @patch("lexigram.cli.commands.dev.ServerManager")
    def test_dev_with_entry_point(self, mock_manager_cls, tmp_path, monkeypatch):
        # Create a minimal main.py
        main_file = tmp_path / "main.py"
        main_file.write_text("print('hello')")
        
        monkeypatch.chdir(tmp_path)
        
        mock_instance = MagicMock()
        mock_manager_cls.return_value = mock_instance
        
        result = self.runner.invoke(app, ["--entry", "main.py", "--no-reload"])
        assert result.exit_code == 0
        assert "Starting dev server" in result.output
        mock_instance.start_dev.assert_called_once()

    @patch("lexigram.cli.commands.dev.ServerManager")
    def test_dev_start_production(self, mock_manager_cls, tmp_path, monkeypatch):
        # Create a minimal main.py
        main_file = tmp_path / "main.py"
        main_file.write_text("print('hello')")
        
        monkeypatch.chdir(tmp_path)
        
        mock_instance = MagicMock()
        mock_manager_cls.return_value = mock_instance
        
        result = self.runner.invoke(app, ["start", "--entry", "main.py", "--workers", "2"])
        assert result.exit_code == 0
        assert "Starting production server" in result.output
        mock_instance.start.assert_called_once()
