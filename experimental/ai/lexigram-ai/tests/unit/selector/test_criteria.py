"""Tests for SelectionCriteria and SelectionStrategy."""

from lexigram.ai.llm.selection.core import (
    DEFAULT_MODEL_CAPABILITIES,
    ModelSelector,
    SelectionCriteria,
    SelectionStrategy,
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

        model = selector.select("Hello")
        assert model == "claude-3-haiku-20240307"

        haiku_caps = selector.get_capabilities("claude-3-haiku-20240307")
        gpt35_caps = selector.get_capabilities("gpt-3.5-turbo")
        assert haiku_caps is not None
        assert gpt35_caps is not None
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

        long_prompt = "word " * 2000
        model = selector.select(long_prompt)
        assert model == "gpt-4-turbo"

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

        model = selector.select("Draft a contract", context={"task_type": "legal"})
        assert model == "gpt-4-turbo"

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

        assert not strategy.matches({})
        assert not strategy.matches({"other_key": 123})
