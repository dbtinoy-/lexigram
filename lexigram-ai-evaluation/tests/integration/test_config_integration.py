"""Integration tests for evaluation using test_bed."""

import pytest
from lexigram.ai.evaluation.config import EvaluationConfig
from lexigram.testing.fixtures import test_bed


class TestEvaluationConfigIntegration:
    """Integration tests for EvaluationConfig."""

    @pytest.mark.asyncio
    async def test_config_in_environment(self, test_bed) -> None:
        """Test config in test environment."""
        config = EvaluationConfig()
        assert config.default_threshold == 0.8

    @pytest.mark.asyncio
    async def test_config_with_threshold(self, test_bed) -> None:
        """Test config threshold in environment."""
        config = EvaluationConfig(default_threshold=0.9)
        assert config.default_threshold == 0.9

    @pytest.mark.asyncio
    async def test_config_embedding_model(self, test_bed) -> None:
        """Test embedding model setting."""
        config = EvaluationConfig(embedding_model="text-embedding-3-large")
        assert config.embedding_model == "text-embedding-3-large"

    @pytest.mark.asyncio
    async def test_config_timeout(self, test_bed) -> None:
        """Test timeout in environment."""
        config = EvaluationConfig(timeout_seconds=120)
        assert config.timeout_seconds == 120

    @pytest.mark.asyncio
    async def test_config_max_samples(self, test_bed) -> None:
        """Test max samples."""
        config = EvaluationConfig(max_samples=100)
        assert config.max_samples == 100


class TestEvaluationEnvironment:
    """Tests for evaluation in test environment."""

    @pytest.mark.asyncio
    async def test_test_bed_context_manager(self, test_bed) -> None:
        """Test bed can be used as context manager."""
        async with test_bed as env:
            assert env is not None