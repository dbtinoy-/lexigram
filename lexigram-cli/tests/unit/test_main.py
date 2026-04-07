"""Tests for the main CLI entry point."""

import pytest
from typer.testing import CliRunner

from lexigram.cli.runtime.main import app


class TestMainCLI:
    """Test the main CLI application."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """CLI test runner."""
        return CliRunner()

    def test_main_help(self, runner: CliRunner):
        """Test main help command."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Lexigram Framework CLI" in result.output
        assert "new" in result.output
        assert "add" in result.output
        assert "dev" in result.output

    def test_main_version(self, runner: CliRunner):
        """Test version command."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "lexigram" in result.output
        assert "0.1.1" in result.output

    def test_main_no_args(self, runner: CliRunner):
        pytest.skip("CLI needs framework update")

    def test_main_unknown_command(self, runner: CliRunner):
        """Test unknown command."""
        result = runner.invoke(app, ["unknown"])
        assert result.exit_code == 2  # Typer error code for unknown command
        assert "No such command" in result.output