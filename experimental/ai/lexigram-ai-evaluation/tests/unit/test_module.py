"""Unit tests for evaluation module."""

from lexigram.ai.evaluation.module import EvaluationModule


class TestEvaluationModule:
    """Tests for EvaluationModule."""

    def test_module_creation(self) -> None:
        """Test module can be instantiated."""
        module = EvaluationModule()
        assert module is not None

    def test_module_configure(self) -> None:
        """Test module configure returns DynamicModule."""
        result = EvaluationModule.configure()
        assert result is not None
        assert hasattr(result, "module")
        assert hasattr(result, "providers")
        assert hasattr(result, "exports")

    def test_module_has_providers(self) -> None:
        """Test module has providers."""
        result = EvaluationModule.configure()
        assert len(result.providers) > 0