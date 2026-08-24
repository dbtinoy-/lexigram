"""Tests for ModelSelector."""

from lexigram.ai.llm.selection.core import ModelSelector, SelectionStrategy


class TestModelSelector:
    """Tests for ModelSelector."""

    def test_basic_creation(self):
        """Test basic selector creation."""
        selector = ModelSelector(default_model="gpt-3.5-turbo")

        assert selector.default_model == "gpt-3.5-turbo"
        assert selector.strategies == []
        assert selector.fallback_chain == ["gpt-3.5-turbo"]

    def test_select_default(self):
        """Test selecting default model."""
        selector = ModelSelector(default_model="gpt-3.5-turbo")

        model = selector.select("Hello world")
        assert model == "gpt-3.5-turbo"

    def test_select_with_strategy(self):
        """Test selecting with matching strategy."""
        selector = ModelSelector(
            default_model="gpt-3.5-turbo",
            strategies=[
                SelectionStrategy(
                    name="long",
                    model="gpt-4",
                    conditions={"min_tokens": 1000},
                ),
            ],
        )

        long_prompt = "x " * 2500
        model = selector.select(long_prompt)
        assert model == "gpt-4"

        model = selector.select("Hello")
        assert model == "gpt-3.5-turbo"

    def test_select_strategy_priority(self):
        """Test strategy selection by priority."""
        selector = ModelSelector(
            default_model="gpt-3.5-turbo",
            strategies=[
                SelectionStrategy(
                    name="low_priority",
                    model="claude-3-haiku-20240307",
                    conditions={"max_tokens": 2000},
                    priority=5,
                ),
                SelectionStrategy(
                    name="high_priority",
                    model="gpt-4",
                    conditions={"max_tokens": 2000},
                    priority=10,
                ),
            ],
        )

        model = selector.select("Short prompt")
        assert model == "gpt-4"

    def test_select_with_context(self):
        """Test selecting with custom context."""
        selector = ModelSelector(
            default_model="gpt-3.5-turbo",
            strategies=[
                SelectionStrategy(
                    name="code",
                    model="gpt-4",
                    conditions={"has_code": True},
                ),
            ],
        )

        model = selector.select("Fix this bug", context={"has_code": True})
        assert model == "gpt-4"

        model = selector.select("Fix this bug")
        assert model == "gpt-3.5-turbo"

    def test_select_with_required_capabilities(self):
        """Test selecting with required capabilities."""
        selector = ModelSelector(default_model="gpt-3.5-turbo")

        model = selector.select(
            "Analyze this image",
            required_capabilities=["supports_vision"],
        )
        assert model in ["gpt-4-turbo", "claude-3-opus-20240229"]

        model = selector.select(
            "Call a function",
            required_capabilities=["supports_functions"],
        )
        caps = selector.get_capabilities(model)
        assert caps is not None
        assert caps.supports_functions is True

    def test_get_fallback(self):
        """Test getting fallback models."""
        selector = ModelSelector(
            fallback_chain=["gpt-4", "gpt-3.5-turbo", "ollama/llama3"],
        )

        assert selector.get_fallback("gpt-4") == "gpt-3.5-turbo"
        assert selector.get_fallback("gpt-3.5-turbo") == "ollama/llama3"
        assert selector.get_fallback("ollama/llama3") is None

    def test_get_fallback_not_in_chain(self):
        """Test fallback for model not in chain."""
        selector = ModelSelector(
            fallback_chain=["gpt-4", "gpt-3.5-turbo"],
        )

        fallback = selector.get_fallback("unknown-model")
        assert fallback == "gpt-4"

    def test_get_capabilities(self):
        """Test getting model capabilities."""
        selector = ModelSelector()

        caps = selector.get_capabilities("gpt-4-turbo")
        assert caps is not None
        assert caps.max_tokens == 128000

        caps = selector.get_capabilities("unknown-model")
        assert caps is None

    def test_estimate_cost(self):
        """Test cost estimation."""
        selector = ModelSelector()

        cost = selector.estimate_cost("gpt-4-turbo", 1000, 500)
        expected = (1000 / 1000 * 10.0) + (500 / 1000 * 30.0)
        assert abs(cost - expected) < 0.001

        cost = selector.estimate_cost("unknown-model", 1000, 500)
        assert cost == 0.0

    def test_build_context(self):
        """Test context building."""
        selector = ModelSelector(default_model="gpt-3.5-turbo")

        ctx = selector._build_context("Hello world", {})
        assert "tokens" in ctx or "token_count" in ctx

        ctx = selector._build_context("```python\ndef foo(): pass\n```", {})
        assert ctx["has_code"] is True

        ctx = selector._build_context("What is Python?", {})
        assert ctx["is_question"] is True

        ctx = selector._build_context("Test", {"custom_key": "value"})
        assert ctx["custom_key"] == "value"

    def test_filter_by_capabilities(self):
        """Test filtering models by capabilities."""
        selector = ModelSelector()

        models = selector._filter_by_capabilities(["supports_vision"])
        assert "gpt-4-turbo" in models
        assert "claude-3-opus-20240229" in models
        assert "gpt-3.5-turbo" not in models

        models = selector._filter_by_capabilities(["supports_functions"])
        assert len(models) > 0
        for model in models:
            caps = selector.get_capabilities(model)
            assert caps.supports_functions is True
