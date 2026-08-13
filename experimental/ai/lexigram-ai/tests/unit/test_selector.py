"""Tests for model selection and routing."""

from lexigram.ai.llm.selection.core import (
    DEFAULT_MODEL_CAPABILITIES,
    ModelCapabilities,
    ModelSelector,
    SelectionCriteria,
    SelectionStrategy,
    create_balanced_selector,
    create_cost_optimized_selector,
    create_quality_optimized_selector,
)


class TestSelectionCriteria:
    """Tests for SelectionCriteria enum and criteria-based routing."""

    def test_enum_members_exist(self):
        """Test that all expected SelectionCriteria members are present."""
        assert SelectionCriteria.TOKEN_COUNT == "token_count"
        assert SelectionCriteria.COST == "cost"
        assert SelectionCriteria.LATENCY == "latency"
        assert SelectionCriteria.QUALITY == "quality"
        assert SelectionCriteria.CUSTOM == "custom"

    def test_enum_values_are_strings(self):
        """Test that SelectionCriteria values are lowercase strings (StrEnum)."""
        for criterion in SelectionCriteria:
            assert isinstance(criterion.value, str)
            assert criterion.value == criterion.value.lower()

    def test_all_criteria_members(self):
        """Test that exactly the documented criteria members are defined."""
        members = {c.value for c in SelectionCriteria}
        assert members == {"token_count", "cost", "latency", "quality", "custom"}

    def test_cost_criteria_selects_cheapest_model(self):
        """Test routing with COST criterion selects cheapest available model."""
        # Build a selector whose strategies reflect cost-based routing:
        # short prompts -> cheapest model, long prompts -> mid-tier
        selector = ModelSelector(
            default_model="gpt-3.5-turbo",
            strategies=[
                SelectionStrategy(
                    name=SelectionCriteria.COST,
                    model="claude-3-haiku-20240307",
                    conditions={"max_tokens": 500},
                    priority=10,
                ),
                SelectionStrategy(
                    name=SelectionCriteria.COST + "_medium",
                    model="gpt-3.5-turbo",
                    conditions={"max_tokens": 2000},
                    priority=9,
                ),
            ],
            model_capabilities=DEFAULT_MODEL_CAPABILITIES,
        )

        # Short prompt: COST strategy picks the cheapest (haiku)
        model = selector.select("Hello")
        assert model == "claude-3-haiku-20240307"

        haiku_caps = selector.get_capabilities("claude-3-haiku-20240307")
        gpt35_caps = selector.get_capabilities("gpt-3.5-turbo")
        assert haiku_caps is not None
        assert gpt35_caps is not None
        # The selected model should be cheaper than gpt-3.5-turbo for input tokens
        assert haiku_caps.cost_per_1k_input <= gpt35_caps.cost_per_1k_input

    def test_quality_criteria_selects_highest_quality_model(self):
        """Test routing with QUALITY criterion selects highest quality model."""
        selector = ModelSelector(
            default_model="gpt-3.5-turbo",
            strategies=[
                SelectionStrategy(
                    name=SelectionCriteria.QUALITY,
                    model="claude-3-opus-20240229",
                    conditions={"min_tokens": 1},
                    priority=10,
                ),
            ],
            model_capabilities=DEFAULT_MODEL_CAPABILITIES,
        )

        model = selector.select("Explain quantum mechanics in detail")
        assert model == "claude-3-opus-20240229"

        opus_caps = selector.get_capabilities("claude-3-opus-20240229")
        gpt35_caps = selector.get_capabilities("gpt-3.5-turbo")
        assert opus_caps is not None
        assert gpt35_caps is not None
        assert opus_caps.quality_score > gpt35_caps.quality_score

    def test_latency_criteria_selects_low_latency_model(self):
        """Test routing with LATENCY criterion selects fastest model."""
        selector = ModelSelector(
            default_model="gpt-4-turbo",
            strategies=[
                SelectionStrategy(
                    name=SelectionCriteria.LATENCY,
                    model="claude-3-haiku-20240307",
                    conditions={"max_tokens": 10000},
                    priority=10,
                ),
            ],
            model_capabilities=DEFAULT_MODEL_CAPABILITIES,
        )

        model = selector.select("Quick answer please")
        assert model == "claude-3-haiku-20240307"

        haiku_caps = selector.get_capabilities("claude-3-haiku-20240307")
        gpt4_caps = selector.get_capabilities("gpt-4-turbo")
        assert haiku_caps is not None
        assert gpt4_caps is not None
        # Haiku should be faster than gpt-4-turbo
        assert haiku_caps.avg_latency_ms < gpt4_caps.avg_latency_ms

    def test_token_count_criteria_routes_by_context_length(self):
        """Test routing with TOKEN_COUNT criterion routes based on prompt length."""
        selector = ModelSelector(
            default_model="gpt-3.5-turbo",
            strategies=[
                SelectionStrategy(
                    name=SelectionCriteria.TOKEN_COUNT,
                    model="gpt-4-turbo",
                    conditions={"min_tokens": 1000},
                    priority=10,
                ),
            ],
            model_capabilities=DEFAULT_MODEL_CAPABILITIES,
        )

        # Long prompt exceeds token threshold -> gpt-4-turbo selected
        long_prompt = "word " * 2000  # ~500 tokens estimated at 4 chars/token
        model = selector.select(long_prompt)
        assert model == "gpt-4-turbo"

        # Short prompt stays at default
        model = selector.select("Hi")
        assert model == "gpt-3.5-turbo"

    def test_custom_criteria_routes_via_context_flag(self):
        """Test routing with CUSTOM criterion using user-supplied context."""
        selector = ModelSelector(
            default_model="gpt-3.5-turbo",
            strategies=[
                SelectionStrategy(
                    name=SelectionCriteria.CUSTOM,
                    model="gpt-4-turbo",
                    conditions={"task_type": "legal"},
                    priority=10,
                ),
            ],
            model_capabilities=DEFAULT_MODEL_CAPABILITIES,
        )

        # Custom context matches the strategy
        model = selector.select("Draft a contract", context={"task_type": "legal"})
        assert model == "gpt-4-turbo"

        # No custom context -> default model
        model = selector.select("Draft a contract")
        assert model == "gpt-3.5-turbo"


class TestSelectionStrategy:
    """Tests for SelectionStrategy."""

    def test_basic_creation(self):
        """Test basic strategy creation."""
        strategy = SelectionStrategy(
            name="test",
            model="gpt-4",
            conditions={"min_tokens": 1000},
        )

        assert strategy.name == "test"
        assert strategy.model == "gpt-4"
        assert strategy.conditions == {"min_tokens": 1000}
        assert strategy.priority == 0

    def test_matches_min_condition(self):
        """Test matching with min_ condition."""
        strategy = SelectionStrategy(
            name="long_context",
            model="gpt-4",
            conditions={"min_tokens": 1000},
        )

        assert strategy.matches({"tokens": 1500})
        assert strategy.matches({"tokens": 1000})
        assert not strategy.matches({"tokens": 500})

    def test_matches_max_condition(self):
        """Test matching with max_ condition."""
        strategy = SelectionStrategy(
            name="short_context",
            model="gpt-3.5-turbo",
            conditions={"max_tokens": 500},
        )

        assert strategy.matches({"tokens": 300})
        assert strategy.matches({"tokens": 500})
        assert not strategy.matches({"tokens": 700})

    def test_matches_boolean_condition(self):
        """Test matching with has_ condition."""
        strategy = SelectionStrategy(
            name="code_task",
            model="gpt-4",
            conditions={"has_code": True},
        )

        assert strategy.matches({"has_code": True})
        assert not strategy.matches({"has_code": False})

    def test_matches_exact_condition(self):
        """Test matching with exact value."""
        strategy = SelectionStrategy(
            name="specific_type",
            model="gpt-4",
            conditions={"task_type": "analysis"},
        )

        assert strategy.matches({"task_type": "analysis"})
        assert not strategy.matches({"task_type": "summary"})

    def test_matches_multiple_conditions(self):
        """Test matching with multiple conditions."""
        strategy = SelectionStrategy(
            name="complex",
            model="gpt-4",
            conditions={
                "min_tokens": 1000,
                "has_code": True,
            },
        )

        assert strategy.matches({"tokens": 1500, "has_code": True})
        assert not strategy.matches({"tokens": 500, "has_code": True})
        assert not strategy.matches({"tokens": 1500, "has_code": False})

    def test_matches_missing_context(self):
        """Test matching when context is missing required key."""
        strategy = SelectionStrategy(
            name="test",
            model="gpt-4",
            conditions={"min_tokens": 1000},
        )

        # Should not match if required key is missing
        assert not strategy.matches({})
        assert not strategy.matches({"other_key": 123})


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
        assert caps.supports_vision is False  # Default
        assert caps.cost_per_1k_input == 10.0

    def test_default_capabilities(self):
        """Test default model capabilities."""
        # Should have capabilities for common models
        assert "gpt-4-turbo" in DEFAULT_MODEL_CAPABILITIES
        assert "gpt-3.5-turbo" in DEFAULT_MODEL_CAPABILITIES
        assert "claude-3-opus-20240229" in DEFAULT_MODEL_CAPABILITIES

        # Check GPT-4 Turbo capabilities
        gpt4 = DEFAULT_MODEL_CAPABILITIES["gpt-4-turbo"]
        assert gpt4.max_tokens == 128000
        assert gpt4.supports_functions is True
        assert gpt4.supports_vision is True


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

        # Long prompt -> GPT-4
        # Need ~4000 characters to get >1000 tokens (4 chars/token estimate)
        long_prompt = "x " * 2500  # Will be >1000 tokens
        model = selector.select(long_prompt)
        assert model == "gpt-4"

        # Short prompt -> default
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

        # Should select high priority strategy
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

        # With code context
        model = selector.select("Fix this bug", context={"has_code": True})
        assert model == "gpt-4"

        # Without code context
        model = selector.select("Fix this bug")
        assert model == "gpt-3.5-turbo"

    def test_select_with_required_capabilities(self):
        """Test selecting with required capabilities."""
        selector = ModelSelector(default_model="gpt-3.5-turbo")

        # Require vision support
        model = selector.select(
            "Analyze this image",
            required_capabilities=["supports_vision"],
        )
        assert model in ["gpt-4-turbo", "claude-3-opus-20240229"]

        # Require function calling
        model = selector.select(
            "Call a function",
            required_capabilities=["supports_functions"],
        )
        # Should be a model with function support
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

        # Should return first fallback
        fallback = selector.get_fallback("unknown-model")
        assert fallback == "gpt-4"

    def test_get_capabilities(self):
        """Test getting model capabilities."""
        selector = ModelSelector()

        caps = selector.get_capabilities("gpt-4-turbo")
        assert caps is not None
        assert caps.max_tokens == 128000

        # Unknown model
        caps = selector.get_capabilities("unknown-model")
        assert caps is None

    def test_estimate_cost(self):
        """Test cost estimation."""
        selector = ModelSelector()

        # GPT-4 Turbo: $10/1M input, $30/1M output
        cost = selector.estimate_cost("gpt-4-turbo", 1000, 500)
        expected = (1000 / 1000 * 10.0) + (500 / 1000 * 30.0)
        assert abs(cost - expected) < 0.001

        # Unknown model should return 0
        cost = selector.estimate_cost("unknown-model", 1000, 500)
        assert cost == 0.0

    def test_build_context(self):
        """Test context building."""
        selector = ModelSelector(default_model="gpt-3.5-turbo")

        # Should add token count
        ctx = selector._build_context("Hello world", {})
        assert "tokens" in ctx or "token_count" in ctx

        # Should detect code
        ctx = selector._build_context("```python\ndef foo(): pass\n```", {})
        assert ctx["has_code"] is True

        # Should detect questions
        ctx = selector._build_context("What is Python?", {})
        assert ctx["is_question"] is True

        # Should preserve user context
        ctx = selector._build_context("Test", {"custom_key": "value"})
        assert ctx["custom_key"] == "value"

    def test_filter_by_capabilities(self):
        """Test filtering models by capabilities."""
        selector = ModelSelector()

        # Filter for vision support
        models = selector._filter_by_capabilities(["supports_vision"])
        assert "gpt-4-turbo" in models
        assert "claude-3-opus-20240229" in models
        assert "gpt-3.5-turbo" not in models

        # Filter for function support
        models = selector._filter_by_capabilities(["supports_functions"])
        assert len(models) > 0
        for model in models:
            caps = selector.get_capabilities(model)
            assert caps.supports_functions is True


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

        # Should select high-quality models
        model = selector.select("x " * 1000)  # Long prompt
        assert model in ["gpt-4-turbo", "claude-3-opus-20240229"]

    def test_balanced_selector(self):
        """Test balanced selector."""
        selector = create_balanced_selector()

        assert selector.default_model == "claude-3-sonnet-20240229"
        assert len(selector.strategies) > 0

        # Short prompt -> fast model
        model = selector.select("Hello")
        caps = selector.get_capabilities(model)
        assert caps is not None
        # Should be relatively cheap
        avg_cost = (caps.cost_per_1k_input + caps.cost_per_1k_output) / 2
        assert avg_cost < 5.0  # Less than $5 per 1K tokens


class TestIntegration:
    """Integration tests."""

    def test_full_workflow(self):
        """Test complete selection workflow."""
        # Create selector
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

        # Test 1: Simple prompt -> default
        model = selector.select("Hello")
        assert model == "gpt-3.5-turbo"

        # Test 2: Long prompt -> complex strategy
        # Need ~2000 characters to get >500 tokens (4 chars/token estimate)
        long_prompt = "x " * 1500
        model = selector.select(long_prompt)
        assert model == "gpt-4"

        # Test 3: Code prompt -> code strategy
        model = selector.select("Fix bug", context={"has_code": True})
        assert model == "gpt-4"

        # Test 4: Get fallback
        fallback = selector.get_fallback("gpt-4")
        assert fallback == "gpt-3.5-turbo"

        # Test 5: Estimate cost
        cost = selector.estimate_cost("gpt-4", 1000, 500)
        assert cost > 0

    def test_capability_based_workflow(self):
        """Test capability-based selection workflow."""
        selector = ModelSelector()

        # Require vision
        model = selector.select(
            "Analyze image",
            required_capabilities=["supports_vision"],
        )
        caps = selector.get_capabilities(model)
        assert caps.supports_vision is True

        # Require functions + vision
        model = selector.select(
            "Call function with image",
            required_capabilities=["supports_vision", "supports_functions"],
        )
        caps = selector.get_capabilities(model)
        assert caps.supports_vision is True
        assert caps.supports_functions is True
