"""Unit tests for evaluation using test_bed fixture."""

import pytest
from lexigram.ai.evaluation.config import EvaluationConfig
from lexigram.testing.fixtures import test_bed


class TestEvaluationWithTestBed:
    """Tests using test_bed fixture."""

    @pytest.mark.asyncio
    async def test_config_in_test_bed(self) -> None:
        """Test config works in test bed."""
        config = EvaluationConfig()
        assert config.default_threshold == 0.8

    @pytest.mark.asyncio
    async def test_config_enabled_default(self) -> None:
        """Test enabled by default."""
        config = EvaluationConfig()
        assert config.enabled is True

    @pytest.mark.asyncio
    async def test_config_timeout(self) -> None:
        """Test timeout setting."""
        config = EvaluationConfig(timeout_seconds=60)
        assert config.timeout_seconds == 60

    @pytest.mark.asyncio
    async def test_config_max_retries(self) -> None:
        """Test max retries."""
        config = EvaluationConfig(max_retries=5)
        assert config.max_retries == 5


class TestEvaluationConfigValidation:
    """Tests for config validation."""

    def test_threshold_validation_low(self) -> None:
        """Test threshold validation low."""
        with pytest.raises(ValueError):
            EvaluationConfig(default_threshold=-0.1)

    def test_threshold_validation_high(self) -> None:
        """Test threshold validation high."""
        with pytest.raises(ValueError):
            EvaluationConfig(default_threshold=1.1)

    def test_timeout_validation_zero(self) -> None:
        """Test timeout cannot be zero."""
        with pytest.raises(ValueError):
            EvaluationConfig(timeout_seconds=0)

    def test_max_retries_validation(self) -> None:
        """Test max retries validation."""
        with pytest.raises(ValueError):
            EvaluationConfig(max_retries=-1)