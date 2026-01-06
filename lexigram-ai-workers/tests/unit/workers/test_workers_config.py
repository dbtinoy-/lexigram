"""Tests for AI workers configuration."""

from __future__ import annotations

import pytest

from lexigram.ai.workers.config import WorkersConfig
from lexigram.ai.workers.constants import ENV_NESTED_DELIMITER, ENV_PREFIX


class TestWorkersConfig:
    def test_default_values(self) -> None:
        """Test WorkersConfig has correct defaults."""
        config = WorkersConfig()
        assert config.enabled is True
        assert config.batch_embedding_concurrency == 3
        assert config.document_ingestion_concurrency == 3
        assert config.enable_maintenance is True
        assert config.dlq_check_interval == 60

    def test_custom_values(self) -> None:
        """Test WorkersConfig accepts custom values."""
        config = WorkersConfig(
            enabled=False,
            batch_embedding_concurrency=5,
            document_ingestion_concurrency=7,
            enable_maintenance=False,
            dlq_check_interval=120,
        )
        assert config.enabled is False
        assert config.batch_embedding_concurrency == 5
        assert config.document_ingestion_concurrency == 7
        assert config.enable_maintenance is False
        assert config.dlq_check_interval == 120

    def test_batch_embedding_concurrency_min_validation(self) -> None:
        """Test batch_embedding_concurrency enforces minimum of 1."""
        config = WorkersConfig(batch_embedding_concurrency=1)
        assert config.batch_embedding_concurrency == 1

    def test_batch_embedding_concurrency_rejects_zero(self) -> None:
        """Test batch_embedding_concurrency rejects 0."""
        with pytest.raises(ValueError):
            WorkersConfig(batch_embedding_concurrency=0)

    def test_batch_embedding_concurrency_rejects_negative(self) -> None:
        """Test batch_embedding_concurrency rejects negative values."""
        with pytest.raises(ValueError):
            WorkersConfig(batch_embedding_concurrency=-1)

    def test_document_ingestion_concurrency_min_validation(self) -> None:
        """Test document_ingestion_concurrency enforces minimum of 1."""
        config = WorkersConfig(document_ingestion_concurrency=1)
        assert config.document_ingestion_concurrency == 1

    def test_document_ingestion_concurrency_rejects_zero(self) -> None:
        """Test document_ingestion_concurrency rejects 0."""
        with pytest.raises(ValueError):
            WorkersConfig(document_ingestion_concurrency=0)

    def test_dlq_check_interval_min_validation(self) -> None:
        """Test dlq_check_interval enforces minimum of 1."""
        config = WorkersConfig(dlq_check_interval=1)
        assert config.dlq_check_interval == 1

    def test_dlq_check_interval_rejects_zero(self) -> None:
        """Test dlq_check_interval rejects 0."""
        with pytest.raises(ValueError):
            WorkersConfig(dlq_check_interval=0)

    def test_dlq_check_interval_rejects_negative(self) -> None:
        """Test dlq_check_interval rejects negative values."""
        with pytest.raises(ValueError):
            WorkersConfig(dlq_check_interval=-1)

    def test_validate_for_environment_returns_empty(self) -> None:
        """Test validate_for_environment returns empty list."""
        config = WorkersConfig()
        issues = config.validate_for_environment()
        assert issues == []

    def test_validate_for_environment_with_env_returns_empty(self) -> None:
        """Test validate_for_environment with env returns empty list."""
        config = WorkersConfig()
        issues = config.validate_for_environment(env="production")
        assert issues == []

    def test_config_section(self) -> None:
        """Test config_section class variable is set correctly."""
        assert WorkersConfig.config_section == "ai_workers"

    def test_env_prefix(self) -> None:
        """Test env_prefix is set from constants."""
        config = WorkersConfig()
        assert config.model_config["env_prefix"] == ENV_PREFIX

    def test_env_nested_delimiter(self) -> None:
        """Test env_nested_delimiter is set from constants."""
        config = WorkersConfig()
        assert config.model_config["env_nested_delimiter"] == ENV_NESTED_DELIMITER

    def test_extra_ignored(self) -> None:
        """Test extra fields are ignored."""
        config = WorkersConfig()
        assert config.model_config["extra"] == "ignore"

    def test_all_fields_serializable(self) -> None:
        """Test all config fields can be accessed."""
        config = WorkersConfig(
            enabled=False,
            batch_embedding_concurrency=10,
            document_ingestion_concurrency=20,
            enable_maintenance=False,
            dlq_check_interval=300,
        )
        fields = [
            config.enabled,
            config.batch_embedding_concurrency,
            config.document_ingestion_concurrency,
            config.enable_maintenance,
            config.dlq_check_interval,
        ]
        assert all(f is not None for f in fields)