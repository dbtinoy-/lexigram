"""Tests for the db command."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from lexigram.cli.commands.db import app


class TestDbCommand:
    """Test the db command functionality."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """CLI test runner."""
        return CliRunner()

    def test_db_init(self, runner: CliRunner, tmp_path: Path):
        """Test db init command."""
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            result = runner.invoke(app, ["init", "custom_migrations"])
            assert result.exit_code == 0
            assert "Created custom_migrations directory" in result.output
            assert Path(td).joinpath("custom_migrations").exists()

    @patch("lexigram.cli.commands.db.get_migration_manager", new_callable=AsyncMock)
    def test_db_migrate_create(self, mock_get_manager, runner: CliRunner, tmp_path: Path):
        """Test db migrate (create) command."""
        mock_manager = AsyncMock()
        mock_manager.create_migration.return_value = "20230101_000000"
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(app, ["migrate", "test_migration"])
        assert result.exit_code == 0
        assert "Created migration 20230101_000000: test_migration" in result.output
        mock_manager.create_migration.assert_called_once_with("test_migration", "-- Add your SQL here")

    @patch("lexigram.cli.commands.db._bootstrap_migration_runner", new_callable=AsyncMock)
    def test_db_upgrade(self, mock_bootstrap, runner: CliRunner, tmp_path: Path):
        """Test db upgrade command."""
        mock_runner = AsyncMock()
        mock_runner.run_migrations.return_value = ["20230101_000000"]
        mock_bootstrap.return_value = mock_runner

        result = runner.invoke(app, ["upgrade"])
        assert result.exit_code == 0
        assert "Applied 20230101_000000" in result.output
        mock_runner.run_migrations.assert_called_once()

    @patch("lexigram.cli.commands.db._bootstrap_migration_runner", new_callable=AsyncMock)
    def test_db_status(self, mock_bootstrap, runner: CliRunner, tmp_path: Path):
        """Test db status command."""
        mock_runner = AsyncMock()
        mock_runner.get_current_version.return_value = None
        mock_runner.get_pending_migrations.return_value = []
        mock_bootstrap.return_value = mock_runner

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "Schema is up to date" in result.output or "No migrations applied" in result.output

    @patch("lexigram.cli.commands.db.get_migration_manager", new_callable=AsyncMock)
    def test_db_seed(self, mock_get_manager, runner: CliRunner, tmp_path: Path):
        """Test db seed command."""
        mock_manager = AsyncMock()
        mock_manager.provider = AsyncMock()
        mock_get_manager.return_value = mock_manager

        # Create a dummy seeder file
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            seeds_dir = Path(td) / "seeds"
            seeds_dir.mkdir()
            (seeds_dir / "test_seeder.py").write_text("def run(provider): pass")
            
            result = runner.invoke(app, ["seed"])
            assert result.exit_code == 0
            assert "Running seeder: seeds/test_seeder.py" in result.output

    @patch("lexigram.cli.commands.db.get_migration_manager", new_callable=AsyncMock)
    def test_db_reset(self, mock_get_manager, runner: CliRunner, tmp_path: Path):
        """Test db reset command."""
        mock_manager = AsyncMock()
        mock_manager.provider = AsyncMock()
        mock_manager.provider.url = "sqlite:///dev.db"
        mock_manager.provider.execute_query.return_value = MagicMock(rows=[])
        mock_get_manager.return_value = mock_manager

        result = runner.invoke(app, ["reset", "--force"])
        assert result.exit_code == 0
        assert "Database cleared" in result.output
        mock_manager.initialize_migration_table.assert_called_once()