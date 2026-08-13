"""Criteria-based evaluator."""

from __future__ import annotations

from typing import Any

from lexigram.ai.evaluation.evaluators.base import BaseEvaluator
from lexigram.contracts.ai.evaluation import (
    EvaluationResult,
    EvaluationScoreType,
    EvaluatorProtocol,
)
from lexigram.logging import get_logger
from lexigram.result import Ok, Result

logger = get_logger(__name__)


class CriteriaEvaluator(BaseEvaluator, EvaluatorProtocol):
    """Rule-based criteria evaluation.

    Evaluates outputs against predefined rules/criteria.
    Supports exact match, contains, regex, and custom predicate checks.
    """

    def __init__(
        self,
        criteria: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(EvaluationScoreType.EXACT_MATCH)
        self._criteria = criteria or []

    @property
    def name(self) -> str:
        return "criteria"

    async def evaluate(
        self,
        input: str,
        output: str,
        reference: str,
    ) -> Result[EvaluationResult, Exception]:
        passed = 0
        total = len(self._criteria) or 1
        details: dict[str, Any] = {"criteria_results": []}

        if not self._criteria:
            exact_match = output.strip().lower() == reference.strip().lower()
            passed = 1 if exact_match else 0
            details["exact_match"] = exact_match
        else:
            for criterion in self._criteria:
                criterion_type = criterion.get("type", "exact_match")
                result = self._evaluate_criterion(
                    criterion_type, output, reference, criterion
                )
                details["criteria_results"].append(result)
                if result.get("passed"):
                    passed += 1

        score = passed / total if total > 0 else 0.0
        feedback = f"Passed {passed}/{total} criteria"

        return Ok(self._create_result(score, feedback, details))

    def _evaluate_criterion(
        self,
        criterion_type: str,
        output: str,
        reference: str,
        criterion: dict[str, Any],
    ) -> dict[str, Any]:
        result = {"type": criterion_type, "passed": False}

        if criterion_type == "exact_match":
            result["passed"] = output.strip().lower() == reference.strip().lower()
        elif criterion_type == "contains":
            expected = criterion.get("expected", "")
            result["passed"] = expected.lower() in output.lower()
        elif criterion_type == "contains_all":
            expected = criterion.get("expected", [])
            result["passed"] = all(e.lower() in output.lower() for e in expected)
        elif criterion_type == "regex":
            import re

            pattern = criterion.get("pattern", "")
            result["passed"] = bool(re.search(pattern, output))

        return result


__all__ = ["CriteriaEvaluator"]
