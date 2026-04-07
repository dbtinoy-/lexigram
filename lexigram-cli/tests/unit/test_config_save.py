"""Tests for ConfigManager.save()."""
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch

from lexigram.cli.config import CLIConfig, ConfigManager


class TestConfigManagerSave:
    @pytest.fixture
    def tmp_config(self, tmp_path: Path):
        """Patch ConfigManager.config_path to a temp file."""
        config_file = tmp_path / "application.yaml"
        with patch.object(ConfigManager, "config_path", config_file):
            yield config_file

    def test_save_creates_file(self, tmp_config):
        config = CLIConfig()
        ConfigManager.save(config)
        assert tmp_config.exists()

    def test_save_roundtrip(self, tmp_config):
        config = CLIConfig()
        ConfigManager.save(config)
        loaded = ConfigManager.load()
        assert loaded is not None
        # Check key fields match (exclude model_config which is Pydantic metadata)
        for field in config.model_dump():
            if field != "model_config":
                assert getattr(loaded, field) == getattr(config, field)

    def test_save_creates_parent_directories(self, tmp_path):
        nested = tmp_path / "deep" / "nested" / "application.yaml"
        with patch.object(ConfigManager, "config_path", nested):
            ConfigManager.save(CLIConfig())
            assert nested.exists()

    def test_save_handles_corrupt_existing_file(self, tmp_config):
        tmp_config.write_bytes(b"NOT VALID TOML !!!")
        # Should not raise - handles corrupt file by starting fresh
        ConfigManager.save(CLIConfig())
        assert tmp_config.exists()

    def test_save_returns_none(self, tmp_config):
        result = ConfigManager.save(CLIConfig())
        assert result is None
