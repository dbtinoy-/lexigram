"""Unit tests for evaluation constants."""

from lexigram.ai.evaluation import constants


class TestEvaluationConstants:
    """Tests for evaluation constants."""

    def test_env_prefix(self) -> None:
        """Test environment variable prefix."""
        assert constants.ENV_PREFIX == "LEX_AI_EVALUATION__"

    def test_env_nested_delimiter(self) -> None:
        """Test nested delimiter."""
        assert constants.ENV_NESTED_DELIMITER == "__"

    def test_default_embedding_model(self) -> None:
        """Test default embedding model."""
        assert constants.DEFAULT_EMBEDDING_MODEL == "text-embedding-3-small"

    def test_default_threshold(self) -> None:
        """Test default threshold."""
        assert constants.DEFAULT_THRESHOLD == 0.8

    def test_default_timeout(self) -> None:
        """Test default timeout."""
        assert constants.DEFAULT_TIMEOUT_SECONDS == 30

    def test_max_retries(self) -> None:
        """Test max retries."""
        assert constants.MAX_RETRIES == 3