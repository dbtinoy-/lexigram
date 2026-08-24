"""Tests for ModelCapabilities."""

from lexigram.ai.llm.selection.core import DEFAULT_MODEL_CAPABILITIES, ModelCapabilities


class TestModelCapabilities:
    """Tests for ModelCapabilities."""

    def test_basic_creation(self):
        """Test basic capabilities creation."""
        caps = ModelCapabilities(
            max_tokens=8192,
            supports_functions=True,
            cost_per_1k_input=10.0,
        )

        assert caps.max_tokens == 8192
        assert caps.supports_functions is True
        assert caps.supports_vision is False
        assert caps.cost_per_1k_input == 10.0

    def test_default_capabilities(self):
        """Test default model capabilities."""
        assert "gpt-4-turbo" in DEFAULT_MODEL_CAPABILITIES
        assert "gpt-3.5-turbo" in DEFAULT_MODEL_CAPABILITIES
        assert "claude-3-opus-20240229" in DEFAULT_MODEL_CAPABILITIES

        gpt4 = DEFAULT_MODEL_CAPABILITIES["gpt-4-turbo"]
        assert gpt4.max_tokens == 128000
        assert gpt4.supports_functions is True
        assert gpt4.supports_vision is True
