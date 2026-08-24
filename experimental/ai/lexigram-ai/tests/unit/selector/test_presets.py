"""Tests for preset selector factories and integration."""

from lexigram.ai.llm.selection.core import (
    ModelSelector,
    SelectionStrategy,
    create_balanced_selector,
    create_cost_optimized_selector,
    create_quality_optimized_selector,
)


class TestPresetSelectors:
    """Tests for preset selector factories."""

    def test_cost_optimized_selector(self):
        """Test cost-optimized selector."""
        selector = create_cost_optimized_selector()

        assert selector.default_model == "gpt-3.5-turbo"
        assert len(selector.strategies) > 0
        assert "claude-3-haiku-20240307" in selector.fallback_chain

    def test_quality_optimized_selector(self):
        """Test quality-optimized selector."""
        selector = create_quality_optimized_selector()

        assert selector.default_model == "gpt-4-turbo"
        assert len(selector.strategies) > 0

        model = selector.select("x " * 1000)
        assert model in ["gpt-4-turbo", "claude-3-opus-20240229"]

    def test_balanced_selector(self):
        """Test balanced selector."""
        selector = create_balanced_selector()

        assert selector.default_model == "claude-3-sonnet-20240229"
        assert len(selector.strategies) > 0

        model = selector.select("Hello")
        caps = selector.get_capabilities(model)
        assert caps is not None
        avg_cost = (caps.cost_per_1k_input + caps.cost_per_1k_output) / 2
        assert avg_cost < 5.0


class TestIntegration:
    """Integration tests."""

    def test_full_workflow(self):
        """Test complete selection workflow."""
        selector = ModelSelector(
            default_model="gpt-3.5-turbo",
            strategies=[
                SelectionStrategy(
                    name="complex",
                    model="gpt-4",
                    conditions={"min_tokens": 500},
                    priority=10,
                ),
                SelectionStrategy(
                    name="code",
                    model="gpt-4",
                    conditions={"has_code": True},
                    priority=9,
                ),
            ],
            fallback_chain=["gpt-4", "gpt-3.5-turbo", "ollama/llama3"],
        )

        model = selector.select("Hello")
        assert model == "gpt-3.5-turbo"

        long_prompt = "x " * 1500
        model = selector.select(long_prompt)
        assert model == "gpt-4"

        model = selector.select("Fix bug", context={"has_code": True})
        assert model == "gpt-4"

        fallback = selector.get_fallback("gpt-4")
        assert fallback == "gpt-3.5-turbo"

        cost = selector.estimate_cost("gpt-4", 1000, 500)
        assert cost > 0

    def test_capability_based_workflow(self):
        """Test capability-based selection workflow."""
        selector = ModelSelector()

        model = selector.select(
            "Analyze image",
            required_capabilities=["supports_vision"],
        )
        caps = selector.get_capabilities(model)
        assert caps.supports_vision is True

        model = selector.select(
            "Call function with image",
            required_capabilities=["supports_vision", "supports_functions"],
        )
        caps = selector.get_capabilities(model)
        assert caps.supports_vision is True
        assert caps.supports_functions is True
