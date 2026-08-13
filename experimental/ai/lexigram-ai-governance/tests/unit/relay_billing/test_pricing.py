"""Tests for relay price calculation and restricted expression evaluation."""

from __future__ import annotations

from decimal import ROUND_DOWN, Decimal

import pytest

from lexigram.ai.governance.relay_billing import (
    PriceSnapshot,
    RelayPricingEngine,
    SimpleCostEstimator,
    evaluate_expression,
)
from lexigram.contracts.ai.governance import RelayBillingError
from lexigram.contracts.ai.relay import RelayUsage

ZERO = Decimal("0")


def make_usage(**overrides: int) -> RelayUsage:
    """Build a RelayUsage with the given token dims."""
    base = {
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "cache_read_tokens": 0,
        "cache_creation_tokens": 0,
        "reasoning_tokens": 0,
        "audio_input_tokens": 0,
        "audio_output_tokens": 0,
        "image_tokens": 0,
    }
    base.update(overrides)
    return RelayUsage(**base)


def per_1_rates(**prices: str) -> PriceSnapshot:
    """Build a PriceSnapshot from per-1M-token string prices."""
    return PriceSnapshot.from_per_1m(
        {name: Decimal(value) for name, value in prices.items()}
    )


class TestPriceSnapshot:
    def test_from_per_1m_builds_expressions(self) -> None:
        snap = per_1_rates(prompt="2.50", completion="10.00")
        assert snap.expressions["prompt"] == "prompt_tokens * 0.0000025"
        assert snap.expressions["completion"] == "completion_tokens * 0.00001"
        assert snap.expressions["cached_prompt"] == "0"

    def test_missing_dimensions_default_to_zero(self) -> None:
        snap = per_1_rates(prompt="2.50")
        assert snap.expressions["completion"] == "0"
        assert snap.expressions["image"] == "0"

    def test_rejects_negative_price(self) -> None:
        with pytest.raises(ValueError):
            per_1_rates(prompt="-2.5")

    def test_rejects_unknown_dimension(self) -> None:
        with pytest.raises(ValueError):
            PriceSnapshot.from_per_1m({"bogus": Decimal("1")})
        with pytest.raises(ValueError):
            PriceSnapshot(expressions={"bogus": "1"})

    def test_rejects_invalid_expression(self) -> None:
        with pytest.raises(ValueError):
            PriceSnapshot(expressions={"prompt": "prompt_tokens ** 2"})
        with pytest.raises(ValueError):
            PriceSnapshot(expressions={"prompt": ""})

    def test_from_per_1m_formats_exponents_plain(self) -> None:
        snap = per_1_rates(prompt="0.001")
        assert snap.expressions["prompt"] == "prompt_tokens * 0.000000001"


class TestExpressionEvaluator:
    def test_literals_are_constants(self) -> None:
        result = evaluate_expression("5", make_usage())
        assert result.is_ok()
        assert result.unwrap() == Decimal("5")

    def test_dimension_values(self) -> None:
        result = evaluate_expression("prompt_tokens", make_usage(prompt_tokens=7))
        assert result.is_ok()
        assert result.unwrap() == Decimal("7")

    def test_arithmetic_and_parentheses(self) -> None:
        usage = make_usage(prompt_tokens=10, completion_tokens=5)
        result = evaluate_expression(
            "(prompt_tokens + completion_tokens) * 2", usage
        )
        assert result.is_ok()
        assert result.unwrap() == Decimal("30")

    def test_min_max_calls(self) -> None:
        usage = make_usage(prompt_tokens=10, completion_tokens=5)
        assert evaluate_expression("min(prompt_tokens, completion_tokens)", usage).unwrap() == Decimal("5")
        assert evaluate_expression("max(prompt_tokens, completion_tokens)", usage).unwrap() == Decimal("10")

    def test_multiply_by_price(self) -> None:
        usage = make_usage(prompt_tokens=100)
        result = evaluate_expression("prompt_tokens * 0.0000025", usage)
        assert result.is_ok()
        assert result.unwrap() == Decimal("0.000250")

    def test_applies_rounding(self) -> None:
        usage = make_usage(prompt_tokens=3)
        half_up = evaluate_expression("prompt_tokens * 0.005", usage, scale=2)
        assert half_up.unwrap() == Decimal("0.02")
        down = evaluate_expression(
            "prompt_tokens * 0.005", usage, scale=2, rounding=ROUND_DOWN
        )
        assert down.unwrap() == Decimal("0.01")

    @pytest.mark.parametrize(
        "expression",
        [
            "prompt_tokens.total",
            "foo(prompt_tokens)",
            "prompt_tokens ** 2",
            "prompt_tokens = 5",
            "prompt_tokens / 0",
            "unknown_dim",
            "1 +",
            "min(prompt_tokens)",
            "",
        ],
    )
    def test_rejects_unsafe_expressions(self, expression: str) -> None:
        usage = make_usage()
        result = evaluate_expression(expression, usage)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), RelayBillingError)
        assert result.unwrap_err().code in ("invalid_usage",)

    def test_rejects_unbounded_recursion(self) -> None:
        deep = "(" * 100 + "prompt_tokens" + ")" * 100
        result = evaluate_expression(deep, make_usage())
        assert result.is_err()

    def test_rejects_negative_dimension(self) -> None:
        usage = RelayUsage(prompt_tokens=-1)
        result = evaluate_expression("prompt_tokens", usage)
        assert result.is_err()

    def test_rejects_non_finite_impossible(self) -> None:
        usage = make_usage(prompt_tokens=10)
        result = evaluate_expression("prompt_tokens / 0", usage)
        assert result.is_err()


class TestPricingEngine:
    def test_all_dimensions_charged_independently(self) -> None:
        usage = make_usage(
            prompt_tokens=100,
            cache_read_tokens=50,
            completion_tokens=25,
            reasoning_tokens=10,
            audio_input_tokens=5,
            audio_output_tokens=4,
            image_tokens=2,
        )
        engine = RelayPricingEngine(
            lambda model, provider, channel: per_1_rates(
                prompt="1.0", cached_prompt="0.5", completion="2.0"
            )
        )
        result = engine.estimate_charge("m", usage)
        assert result.is_ok()
        breakdown = result.unwrap()
        assert breakdown.prompt == Decimal("0.000100")
        assert breakdown.cached_prompt == Decimal("0.000025")
        assert breakdown.completion == Decimal("0.000050")
        assert breakdown.reasoning == ZERO
        assert breakdown.audio_input == ZERO
        assert breakdown.audio_output == ZERO
        assert breakdown.image == ZERO
        assert breakdown.total == Decimal("0.000175")

    def test_explicit_zero_retained_in_breakdown(self) -> None:
        engine = RelayPricingEngine(lambda _m, _p, _c: per_1_rates(prompt="1.0"))
        result = engine.estimate_charge("m", make_usage(prompt_tokens=10))
        assert result.is_ok()
        breakdown = result.unwrap()
        assert breakdown.audio_input == ZERO
        assert breakdown.image == ZERO
        assert breakdown.reasoning == ZERO

    def test_unknown_price_fails_closed(self) -> None:
        engine = RelayPricingEngine(lambda _m, _p, _c: None)
        result = engine.estimate_charge("unknown-model", make_usage())
        assert result.is_err()
        assert result.unwrap_err().code == "unknown_price"

    def test_negative_usage_fails_closed(self) -> None:
        engine = RelayPricingEngine(lambda _m, _p, _c: per_1_rates(prompt="1.0"))
        result = engine.estimate_charge("m", RelayUsage(prompt_tokens=-1))
        assert result.is_err()
        assert result.unwrap_err().code == "invalid_usage"

    def test_charge_above_maximum_fails_closed(self) -> None:
        engine = RelayPricingEngine(
            lambda _m, _p, _c: per_1_rates(prompt="1000000.0"),
            max_charge=Decimal("1"),
        )
        result = engine.estimate_charge("m", make_usage(prompt_tokens=100))
        assert result.is_err()
        assert result.unwrap_err().code == "charge_overflow"

    def test_token_count_above_maximum_fails_closed(self) -> None:
        engine = RelayPricingEngine(
            lambda _m, _p, _c: per_1_rates(prompt="1.0"),
            max_tokens=10,
        )
        result = engine.estimate_charge("m", make_usage(prompt_tokens=100))
        assert result.is_err()
        assert result.unwrap_err().code == "invalid_usage"

    def test_per_dimension_rounding_overrides(self) -> None:
        engine = RelayPricingEngine(
            lambda _m, _p, _c: per_1_rates(prompt="0.5", completion="0.5"),
            dimension_scales={"completion": 0},
        )
        result = engine.estimate_charge(
            "m", make_usage(prompt_tokens=3, completion_tokens=3)
        )
        assert result.is_ok()
        breakdown = result.unwrap()
        assert breakdown.prompt == Decimal("0.0000015")
        assert breakdown.completion == ZERO
        assert breakdown.total == Decimal("0.0000015")

    def test_expression_error_is_invalid_usage(self) -> None:
        engine = RelayPricingEngine(
            lambda _m, _p, _c: PriceSnapshot(expressions={"prompt": "1/0"})
        )
        result = engine.estimate_charge("m", make_usage(prompt_tokens=10))
        assert result.is_err()
        assert result.unwrap_err().code == "invalid_usage"

    def test_rejects_bad_engine_config(self) -> None:
        with pytest.raises(ValueError):
            RelayPricingEngine(lambda _m, _p, _c: None, scale=-1)
        with pytest.raises(ValueError):
            RelayPricingEngine(lambda _m, _p, _c: None, max_charge=Decimal("-1"))
        with pytest.raises(ValueError):
            RelayPricingEngine(lambda _m, _p, _c: None, dimension_scales={"bogus": 2})


class _FakeEstimator:
    """Minimal ``CostEstimatorProtocol`` double."""

    def estimate_cost(
        self,
        model: str,
        total_tokens: int,
        provider: str | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> float:
        if model == "unknown":
            return 0.0
        return prompt_tokens * 0.0000025 + completion_tokens * 0.00001


class TestSimpleCostEstimator:
    def test_presents_prompt_and_completion_split(self) -> None:
        estimator = SimpleCostEstimator(_FakeEstimator())
        result = estimator.estimate_charge(
            "m", make_usage(prompt_tokens=100, completion_tokens=50)
        )
        assert result.is_ok()
        breakdown = result.unwrap()
        assert breakdown.prompt == Decimal("0.000250")
        assert breakdown.completion == Decimal("0.000500")
        assert breakdown.total == Decimal("0.000750")
        assert breakdown.reasoning == ZERO
        assert breakdown.audio_input == ZERO

    def test_unknown_model_is_zero_charge(self) -> None:
        estimator = SimpleCostEstimator(_FakeEstimator())
        result = estimator.estimate_charge("unknown", make_usage())
        assert result.is_ok()
        assert result.unwrap().total == ZERO

    def test_rejects_bad_config(self) -> None:
        with pytest.raises(ValueError):
            SimpleCostEstimator(_FakeEstimator(), scale=-1)
        with pytest.raises(ValueError):
            SimpleCostEstimator(_FakeEstimator(), max_charge=Decimal("-1"))


class _BadEstimator:
    """CostEstimator double returning a non-finite cost."""

    def estimate_cost(
        self,
        model: str,
        total_tokens: int,
        provider: str | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> float:
        return float("inf")


class TestSimpleCostEstimatorSafety:
    def test_non_finite_cost_fails_closed(self) -> None:
        estimator = SimpleCostEstimator(_BadEstimator())
        result = estimator.estimate_charge("m", make_usage())
        assert result.is_err()
        assert result.unwrap_err().code == "invalid_usage"