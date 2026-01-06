"""Unit tests for evaluation evaluators."""

from __future__ import annotations

import pytest

from lexigram.ai.evaluation.evaluators.criteria import CriteriaEvaluator
from lexigram.ai.evaluation.evaluators.qa import QAEvaluator
from lexigram.ai.evaluation.evaluators.string_distance import StringDistanceEvaluator


class TestCriteriaEvaluator:
    """Tests for CriteriaEvaluator."""

    @pytest.mark.asyncio
    async def test_exact_match_criteria(self) -> None:
        evaluator = CriteriaEvaluator()
        result = await evaluator.evaluate(
            "What is 2+2?",
            "4",
            "4",
        )
        assert result.unwrap().score == 1.0
        assert "Passed 1/1" in result.unwrap().feedback

    @pytest.mark.asyncio
    async def test_exact_match_no_match(self) -> None:
        evaluator = CriteriaEvaluator()
        result = await evaluator.evaluate(
            "What is 2+2?",
            "5",
            "4",
        )
        assert result.unwrap().score == 0.0

    @pytest.mark.asyncio
    async def test_contains_criteria(self) -> None:
        evaluator = CriteriaEvaluator(
            criteria=[{"type": "contains", "expected": "error"}]
        )
        result = await evaluator.evaluate(
            "Check log",
            "Error: something failed",
            "expected output",
        )
        assert result.unwrap().score == 1.0

    @pytest.mark.asyncio
    async def test_contains_all_criteria(self) -> None:
        evaluator = CriteriaEvaluator(
            criteria=[{"type": "contains_all", "expected": ["error", "failed"]}]
        )
        result = await evaluator.evaluate(
            "Check log",
            "Error: something failed",
            "expected output",
        )
        assert result.unwrap().score == 1.0


class TestQAEvaluator:
    """Tests for QAEvaluator."""

    @pytest.mark.asyncio
    async def test_perfect_keyword_match(self) -> None:
        evaluator = QAEvaluator()
        result = await evaluator.evaluate(
            "What is the capital of France?",
            "Paris is the capital of France",
            "Paris",
        )
        assert result.unwrap().score > 0.5

    @pytest.mark.asyncio
    async def test_no_match(self) -> None:
        evaluator = QAEvaluator()
        result = await evaluator.evaluate(
            "What is the capital of France?",
            "London is the capital",
            "Paris",
        )
        assert result.unwrap().score == 0.0


class TestStringDistanceEvaluator:
    """Tests for StringDistanceEvaluator."""

    @pytest.mark.asyncio
    async def test_identical_strings(self) -> None:
        evaluator = StringDistanceEvaluator()
        result = await evaluator.evaluate(
            "Test",
            "hello world",
            "hello world",
        )
        assert result.unwrap().score == 1.0

    @pytest.mark.asyncio
    async def test_different_strings(self) -> None:
        evaluator = StringDistanceEvaluator()
        result = await evaluator.evaluate(
            "Test",
            "hello",
            "world",
        )
        assert result.unwrap().score < 1.0

    @pytest.mark.asyncio
    async def test_jaccard_similarity(self) -> None:
        evaluator = StringDistanceEvaluator(metric="jaccard")
        result = await evaluator.evaluate(
            "Test",
            "hello world",
            "hello world",
        )
        assert result.unwrap().score == 1.0


class TestEvaluatorProtocol:
    """Tests for EvaluatorProtocol."""

    @pytest.mark.asyncio
    async def test_evaluator_has_name_property(self) -> None:
        """Evaluator should have a name property."""
        from lexigram.ai.evaluation.evaluators.criteria import CriteriaEvaluator

        evaluator = CriteriaEvaluator()
        assert evaluator.name == "criteria"

    @pytest.mark.asyncio
    async def test_evaluator_returns_evaluation_result(self) -> None:
        """Evaluator should return EvaluationResult."""
        from lexigram.ai.evaluation.evaluators.criteria import CriteriaEvaluator
        from lexigram.contracts.ai.evaluation import EvaluationResult

        evaluator = CriteriaEvaluator()
        result = await evaluator.evaluate("q", "a", "ref")
        assert isinstance(result.unwrap(), EvaluationResult)
        assert 0.0 <= result.unwrap().score <= 1.0

    @pytest.mark.asyncio
    async def test_evaluator_feedback_includes_score(self) -> None:
        """Evaluator feedback should include score information."""
        from lexigram.ai.evaluation.evaluators.criteria import CriteriaEvaluator

        evaluator = CriteriaEvaluator()
        result = await evaluator.evaluate("q", "answer", "answer")
        assert result.unwrap().feedback is not None
        assert len(result.unwrap().feedback) > 0

    @pytest.mark.asyncio
    async def test_evaluator_metrics_included(self) -> None:
        """Evaluator should include metrics in result."""
        from lexigram.ai.evaluation.evaluators.criteria import CriteriaEvaluator

        evaluator = CriteriaEvaluator()
        result = await evaluator.evaluate("q", "a", "ref")
        assert result.unwrap().metrics is not None
        assert isinstance(result.unwrap().metrics, dict)


class TestCriteriaEvaluatorAdvanced:
    """Advanced tests for CriteriaEvaluator."""

    @pytest.mark.asyncio
    async def test_contains_case_insensitive(self) -> None:
        """Contains criteria should be case insensitive."""
        from lexigram.ai.evaluation.evaluators.criteria import CriteriaEvaluator

        evaluator = CriteriaEvaluator(
            criteria=[{"type": "contains", "expected": "ERROR"}]
        )
        result = await evaluator.evaluate(
            "Check log",
            "error: something failed",
            "ref",
        )
        assert result.unwrap().score == 1.0

    @pytest.mark.asyncio
    async def test_regex_criteria(self) -> None:
        """Criteria evaluator should support regex."""
        from lexigram.ai.evaluation.evaluators.criteria import CriteriaEvaluator

        evaluator = CriteriaEvaluator(
            criteria=[{"type": "regex", "pattern": r"Error.*\d+"}]
        )
        result = await evaluator.evaluate(
            "Check",
            "Error: 404 not found",
            "ref",
        )
        assert result.unwrap().score == 1.0

    @pytest.mark.asyncio
    async def test_multiple_criteria_partial_pass(self) -> None:
        """Multiple criteria should calculate partial score."""
        from lexigram.ai.evaluation.evaluators.criteria import CriteriaEvaluator

        evaluator = CriteriaEvaluator(
            criteria=[
                {"type": "contains", "expected": "error"},
                {"type": "contains", "expected": "failed"},
            ]
        )
        result = await evaluator.evaluate(
            "Log check",
            "Error: failed operation",
            "ref",
        )
        assert result.unwrap().score == 1.0

    @pytest.mark.asyncio
    async def test_empty_criteria_defaults_to_exact_match(self) -> None:
        """Empty criteria defaults to exact match."""
        from lexigram.ai.evaluation.evaluators.criteria import CriteriaEvaluator

        evaluator = CriteriaEvaluator(criteria=[])
        result = await evaluator.evaluate("q", "answer", "answer")
        assert result.unwrap().score == 1.0

    @pytest.mark.asyncio
    async def test_exact_match_case_insensitive(self) -> None:
        """Exact match should be case insensitive."""
        from lexigram.ai.evaluation.evaluators.criteria import CriteriaEvaluator

        evaluator = CriteriaEvaluator()
        result = await evaluator.evaluate("q", "ANSWER", "answer")
        assert result.unwrap().score == 1.0
