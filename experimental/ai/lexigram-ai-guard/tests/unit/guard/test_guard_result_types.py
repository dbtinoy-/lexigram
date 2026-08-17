"""Tests for guard result types (GuardCheckResult, AggregateGuardResult)."""

from __future__ import annotations

import pytest

from lexigram.ai.guard.pipeline.result import (
    AggregateGuardResult,
    GuardAction,
    GuardCheckResult,
)


class TestGuardCheckResult:
    """Test GuardCheckResult value object creation and properties."""

    def test_allow_creates_passing_result(self) -> None:
        """Guard.allow() should create a result with PASS action."""
        result = GuardCheckResult.allow("test_guard", severity="low")

        assert result.guard_name == "test_guard"
        assert result.passed is True
        assert result.action == GuardAction.PASS
        assert result.details == {"severity": "low"}
        assert result.redacted_content is None

    def test_block_creates_blocking_result(self) -> None:
        """Guard.block() should create a result with BLOCK action."""
        result = GuardCheckResult.block(
            "test_guard",
            reason="injection detected",
            confidence=0.95,
        )

        assert result.guard_name == "test_guard"
        assert result.passed is False
        assert result.action == GuardAction.BLOCK
        assert result.details == {"reason": "injection detected", "confidence": 0.95}
        assert result.redacted_content is None

    def test_warn_creates_warning_result(self) -> None:
        """Guard.warn() should create a result with WARN action."""
        result = GuardCheckResult.warn(
            "test_guard",
            reason="borderline input",
        )

        assert result.guard_name == "test_guard"
        assert result.passed is True
        assert result.action == GuardAction.WARN
        assert result.details == {"reason": "borderline input"}

    def test_redact_creates_redaction_result(self) -> None:
        """Guard.redact() should create a result with REDACT action and redacted content."""
        result = GuardCheckResult.redact(
            "pii_guard",
            redacted_content="Hello [REDACTED]",
            reason="SSN detected",
            entity_type="SSN",
        )

        assert result.guard_name == "pii_guard"
        assert result.passed is True
        assert result.action == GuardAction.REDACT
        assert result.redacted_content == "Hello [REDACTED]"
        assert result.details == {"reason": "SSN detected", "entity_type": "SSN"}

    def test_check_result_is_frozen(self) -> None:
        """GuardCheckResult should be immutable (frozen dataclass)."""
        result = GuardCheckResult.allow("test")

        with pytest.raises(AttributeError):
            result.passed = False


class TestAggregateGuardResult:
    """Test AggregateGuardResult aggregation logic."""

    def test_aggregate_with_all_pass_results(self) -> None:
        """Aggregate of all PASS results should be PASS."""
        results = [
            GuardCheckResult.allow("guard1"),
            GuardCheckResult.allow("guard2"),
        ]

        aggregate = AggregateGuardResult.from_results(results, "original content")

        assert aggregate.passed is True
        assert aggregate.action == GuardAction.PASS
        assert aggregate.final_content == "original content"
        assert len(aggregate.results) == 2
        assert aggregate.blocked is False
        assert aggregate.redacted is False

    def test_aggregate_with_warn_result(self) -> None:
        """Aggregate with WARN should have WARN as action."""
        results = [
            GuardCheckResult.allow("guard1"),
            GuardCheckResult.warn("guard2", reason="borderline"),
        ]

        aggregate = AggregateGuardResult.from_results(results, "content")

        assert aggregate.passed is True
        assert aggregate.action == GuardAction.WARN
        assert aggregate.warned is True

    def test_aggregate_with_redact_result(self) -> None:
        """Aggregate with REDACT should use redacted content."""
        results = [
            GuardCheckResult.allow("guard1"),
            GuardCheckResult.redact(
                "guard2",
                redacted_content="Hello [REDACTED]",
                reason="PII detected",
            ),
        ]

        aggregate = AggregateGuardResult.from_results(results, "Hello <number>")

        assert aggregate.passed is True
        assert aggregate.action == GuardAction.REDACT
        assert aggregate.redacted is True
        assert aggregate.final_content == "Hello [REDACTED]"

    def test_aggregate_with_block_result_stops_evaluation(self) -> None:
        """Aggregate with BLOCK should have PASS=False and action=BLOCK."""
        results = [
            GuardCheckResult.allow("guard1"),
            GuardCheckResult.block("guard2", reason="injection detected"),
        ]

        aggregate = AggregateGuardResult.from_results(results, "content")

        assert aggregate.passed is False
        assert aggregate.action == GuardAction.BLOCK
        assert aggregate.blocked is True
        assert aggregate.final_content is None  # Blocked content has no final content
        assert aggregate.blocking_result is not None
        assert aggregate.blocking_result.guard_name == "guard2"

    def test_aggregate_severity_ordering_block_highest(self) -> None:
        """BLOCK should be the highest severity."""
        results = [
            GuardCheckResult.warn("guard1", reason="warning"),
            GuardCheckResult.redact("guard2", redacted_content="redacted", reason="pii"),
            GuardCheckResult.block("guard3", reason="injection"),
        ]

        aggregate = AggregateGuardResult.from_results(results, "content")

        assert aggregate.action == GuardAction.BLOCK
        assert aggregate.blocked is True

    def test_aggregate_severity_ordering_redact_over_warn(self) -> None:
        """REDACT severity should be higher than WARN."""
        results = [
            GuardCheckResult.warn("guard1", reason="warning"),
            GuardCheckResult.redact("guard2", redacted_content="safe", reason="pii"),
        ]

        aggregate = AggregateGuardResult.from_results(results, "content")

        assert aggregate.action == GuardAction.REDACT
        assert aggregate.final_content == "safe"

    def test_blocking_result_property_returns_none_when_no_block(self) -> None:
        """blocking_result should return None if no block action present."""
        results = [
            GuardCheckResult.allow("guard1"),
            GuardCheckResult.warn("guard2", reason="warning"),
        ]

        aggregate = AggregateGuardResult.from_results(results, "content")

        assert aggregate.blocking_result is None

    def test_aggregate_with_empty_results(self) -> None:
        """Aggregate of empty results list should be PASS."""
        aggregate = AggregateGuardResult.from_results([], "content")

        assert aggregate.passed is True
        assert aggregate.action == GuardAction.PASS
        assert aggregate.final_content == "content"

    def test_aggregate_is_frozen(self) -> None:
        """AggregateGuardResult should be immutable (frozen dataclass)."""
        aggregate = AggregateGuardResult.from_results([], "content")

        with pytest.raises(AttributeError):
            aggregate.passed = False


class TestGuardAction:
    """Test GuardAction enum."""

    def test_guard_action_values(self) -> None:
        """GuardAction should have all required values."""
        assert GuardAction.PASS == "pass"
        assert GuardAction.BLOCK == "block"
        assert GuardAction.WARN == "warn"
        assert GuardAction.REDACT == "redact"

    def test_guard_action_is_str_enum(self) -> None:
        """GuardAction should be usable as strings."""
        action = GuardAction.BLOCK
        assert isinstance(action, str)
        assert action == "block"
        assert str(action) == "block"
