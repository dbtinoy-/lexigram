"""Unit tests for EvaluationConfig."""

import pytest
from lexigram.ai.evaluation.config import EvaluationConfig


class TestEvaluationConfig:
    """Tests for EvaluationConfig."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = EvaluationConfig()
        assert config.enabled is True
        assert config.default_threshold == 0.8
        assert config.embedding_model == "text-embedding-3-small"
        assert config.include_metadata is True
        assert config.max_samples is None
        assert config.max_retries == 3
        assert config.timeout_seconds == 30

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = EvaluationConfig(
            enabled=False,
            default_threshold=0.9,
            embedding_model="text-embedding-3-large",
            include_metadata=False,
            max_samples=100,
            max_retries=5,
            timeout_seconds=60,
        )
        assert config.enabled is False
        assert config.default_threshold == 0.9
        assert config.embedding_model == "text-embedding-3-large"
        assert config.include_metadata is False
        assert config.max_samples == 100
        assert config.max_retries == 5
        assert config.timeout_seconds == 60

    def test_threshold_validation(self) -> None:
        """Test threshold must be between 0 and 1."""
        with pytest.raises(ValueError):
            EvaluationConfig(default_threshold=1.5)
        with pytest.raises(ValueError):
            EvaluationConfig(default_threshold=-0.5)

    def test_max_samples_validation(self) -> None:
        """Test max_samples must be positive."""
        with pytest.raises(ValueError):
            EvaluationConfig(max_samples=0)

    def test_timeout_validation(self) -> None:
        """Test timeout must be at least 1."""
        with pytest.raises(ValueError):
            EvaluationConfig(timeout_seconds=0)

    def test_config_section(self) -> None:
        """Test config section name."""
        assert EvaluationConfig.config_section == "ai_evaluation"