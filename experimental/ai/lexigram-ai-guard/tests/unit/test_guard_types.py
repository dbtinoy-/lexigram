"""Tests for guard types — GuardAction enum and result dataclasses."""

from __future__ import annotations

import pytest
from lexigram.ai.guard.types import (
    AggregateGuardResult,
    GuardAction,
    GuardCheckResult,
)


class TestGuardAction:
    """Tests for GuardAction StrEnum."""

    @pytest.mark.parametrize(
        ("member", "expected_value"),
        [
            (GuardAction.PASS, "pass"),
            (GuardAction.BLOCK, "block"),
            (GuardAction.WARN, "warn"),
            (GuardAction.REDACT, "redact"),
        ],
    )
    def test_guard_action_values(self, member: GuardAction, expected_value: str) -> None:
        assert member.value == expected_value

    def test_guard_action_is_str(self) -> None:
        assert isinstance(GuardAction.PASS, str)

    def test_guard_action_comparison(self) -> None:
        assert GuardAction.PASS == "pass"
        assert GuardAction.BLOCK == "block"
        assert GuardAction.WARN == "warn"
        assert GuardAction.REDACT == "redact"

    def test_guard_action_enum_members(self) -> None:
        assert list(GuardAction) == [
            GuardAction.PASS,
            GuardAction.BLOCK,
            GuardAction.WARN,
            GuardAction.REDACT,
        ]


class TestGuardCheckResult:
    """Tests for GuardCheckResult dataclass."""

    def test_guard_check_result_basic_creation(self) -> None:
        result = GuardCheckResult(
            guard_name="test_guard",
            passed=True,
            action="pass",
            details={"key": "value"},
        )
        assert result.guard_name == "test_guard"
        assert result.passed is True
        assert result.action == "pass"
        assert result.details == {"key": "value"}

    def test_guard_check_result_is_frozen(self) -> None:
        result = GuardCheckResult(
            guard_name="test",
            passed=True,
            action="pass",
        )
        with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
            result.passed = False  # type: ignore[assignment]

    def test_guard_check_result_allow_factory(self) -> None:
        result = GuardCheckResult.allow("my_guard", extra_info="test")
        assert result.guard_name == "my_guard"
        assert result.passed is True
        assert result.action == GuardAction.PASS
        assert result.details == {"extra_info": "test"}

    def test_guard_check_result_block_factory(self) -> None:
        result = GuardCheckResult.block("my_guard", reason="unsafe content")
        assert result.guard_name == "my_guard"
        assert result.passed is False
        assert result.action == GuardAction.BLOCK
        assert result.details["reason"] == "unsafe content"

    def test_guard_check_result_warn_factory(self) -> None:
        result = GuardCheckResult.warn("my_guard", reason="borderline")
        assert result.guard_name == "my_guard"
        assert result.passed is True
        assert result.action == GuardAction.WARN
        assert result.details["reason"] == "borderline"

    def test_guard_check_result_redact_factory(self) -> None:
        original = "sensitive data here"
        redacted = "*************"
        result = GuardCheckResult.redact("my_guard", redacted, reason="PII detected")
        assert result.guard_name == "my_guard"
        assert result.passed is True
        assert result.action == GuardAction.REDACT
        assert result.redacted_content == redacted
        assert result.details["reason"] == "PII detected"


class TestAggregateGuardResult:
    """Tests for AggregateGuardResult dataclass."""

    def test_aggregate_guard_result_is_frozen(self) -> None:
        result = AggregateGuardResult(
            passed=True,
            action="pass",
            results=[],
        )
        with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
            result.passed = False  # type: ignore[assignment]

    def test_aggregate_from_results_all_pass(self) -> None:
        results = [
            GuardCheckResult.allow("guard1"),
            GuardCheckResult.allow("guard2"),
        ]
        aggregate = AggregateGuardResult.from_results(results, "original content")
        assert aggregate.passed is True
        assert aggregate.action == GuardAction.PASS
        assert aggregate.results == results

    def test_aggregate_from_results_with_block(self) -> None:
        results = [
            GuardCheckResult.allow("guard1"),
            GuardCheckResult.block("guard2", reason="unsafe"),
            GuardCheckResult.allow("guard3"),
        ]
        aggregate = AggregateGuardResult.from_results(results, "original content")
        assert aggregate.passed is False
        assert aggregate.action == GuardAction.BLOCK

    def test_aggregate_from_results_with_redact(self) -> None:
        results = [
            GuardCheckResult.allow("guard1"),
            GuardCheckResult.redact("guard2", "redacted content", reason="PII"),
        ]
        aggregate = AggregateGuardResult.from_results(results, "original content")
        assert aggregate.passed is True
        assert aggregate.action == GuardAction.REDACT

    def test_aggregate_from_results_with_warn(self) -> None:
        results = [
            GuardCheckResult.allow("guard1"),
            GuardCheckResult.warn("guard2", reason="borderline"),
        ]
        aggregate = AggregateGuardResult.from_results(results, "original")
        assert aggregate.passed is True
        assert aggregate.action == GuardAction.WARN

    def test_aggregate_blocked_property_true(self) -> None:
        aggregate = AggregateGuardResult(
            passed=False,
            action=GuardAction.BLOCK,
            results=[],
        )
        assert aggregate.blocked is True

    def test_aggregate_blocked_property_false(self) -> None:
        aggregate = AggregateGuardResult(
            passed=True,
            action=GuardAction.PASS,
            results=[],
        )
        assert aggregate.blocked is False

    def test_aggregate_redacted_property_true(self) -> None:
        aggregate = AggregateGuardResult(
            passed=True,
            action=GuardAction.REDACT,
            results=[],
        )
        assert aggregate.redacted is True

    def test_aggregate_redacted_property_false(self) -> None:
        aggregate = AggregateGuardResult(
            passed=True,
            action=GuardAction.PASS,
            results=[],
        )
        assert aggregate.redacted is False

    def test_aggregate_warned_property_true(self) -> None:
        aggregate = AggregateGuardResult(
            passed=True,
            action=GuardAction.WARN,
            results=[],
        )
        assert aggregate.warned is True

    def test_aggregate_warned_property_false(self) -> None:
        aggregate = AggregateGuardResult(
            passed=True,
            action=GuardAction.PASS,
            results=[],
        )
        assert aggregate.warned is False

    def test_aggregate_blocking_result_returns_result(self) -> None:
        blocking = GuardCheckResult.block("guard2", reason="unsafe")
        results = [
            GuardCheckResult.allow("guard1"),
            blocking,
        ]
        aggregate = AggregateGuardResult.from_results(results, "content")
        assert aggregate.blocking_result == blocking

    def test_aggregate_blocking_result_returns_none(self) -> None:
        results = [
            GuardCheckResult.allow("guard1"),
            GuardCheckResult.warn("guard2", reason="warning"),
        ]
        aggregate = AggregateGuardResult.from_results(results, "content")
        assert aggregate.blocking_result is None

    def test_aggregate_severity_order_block_over_redact(self) -> None:
        results = [
            GuardCheckResult.redact("guard1", "redacted", reason="pii"),
            GuardCheckResult.block("guard2", reason="unsafe"),
        ]
        aggregate = AggregateGuardResult.from_results(results, "content")
        assert aggregate.action == GuardAction.BLOCK

    def test_aggregate_severity_order_redact_over_warn(self) -> None:
        results = [
            GuardCheckResult.warn("guard1", reason="borderline"),
            GuardCheckResult.redact("guard2", "redacted", reason="pii"),
        ]
        aggregate = AggregateGuardResult.from_results(results, "content")
        assert aggregate.action == GuardAction.REDACT

    def test_aggregate_final_content_set_when_not_blocked(self) -> None:
        results = [
            GuardCheckResult.allow("guard1"),
        ]
        aggregate = AggregateGuardResult.from_results(results, "original")
        assert aggregate.final_content == "original"

    def test_aggregate_final_content_none_when_blocked(self) -> None:
        results = [
            GuardCheckResult.block("guard1", reason="unsafe"),
        ]
        aggregate = AggregateGuardResult.from_results(results, "original")
        assert aggregate.final_content is None