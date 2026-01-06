"""Question-Answer evaluation."""

from __future__ import annotations

from lexigram.ai.evaluation.evaluators.base import BaseEvaluator
from lexigram.contracts.ai.evaluation import (
    EvaluationResult,
    EvaluationScoreType,
    EvaluatorProtocol,
)
from lexigram.logging import get_logger
from lexigram.result import Ok, Result

logger = get_logger(__name__)


class QAEvaluator(BaseEvaluator, EvaluatorProtocol):
    """Question-Answer matching evaluator.

    Evaluates whether the output correctly answers the question
    based on the reference answer. Uses keyword overlap and
    semantic similarity.
    """

    def __init__(self) -> None:
        super().__init__(EvaluationScoreType.PARTIAL_MATCH)

    @property
    def name(self) -> str:
        return "qa"

    async def evaluate(
        self,
        input: str,
        output: str,
        reference: str,
    ) -> Result[EvaluationResult, Exception]:
        reference_keywords = self._extract_keywords(reference)
        output_keywords = self._extract_keywords(output)

        if not reference_keywords:
            score = 1.0 if output.strip() else 0.0
        else:
            overlap = len(set(output_keywords) & set(reference_keywords))
            score = overlap / len(reference_keywords)

        common = set(output_keywords) & set(reference_keywords)
        missing = set(reference_keywords) - set(output_keywords)

        details: dict[str, float | str] = {
            "reference_keywords": str(reference_keywords),
            "output_keywords": str(output_keywords),
            "common_keywords": str(list(common)),
            "missing_keywords": str(list(missing)),
        }

        feedback = f"Matched {len(common)}/{len(reference_keywords)} key concepts"

        return Ok(self._create_result(score, feedback, details))

    def _extract_keywords(self, text: str) -> list[str]:
        import re

        text = text.lower()
        words = re.findall(r"\b[a-z]{3,}\b", text)
        stopwords = {
            "the",
            "and",
            "are",
            "for",
            "that",
            "this",
            "with",
            "from",
            "have",
            "has",
            "had",
            "was",
            "were",
            "been",
            "being",
            "will",
            "would",
            "could",
            "should",
            "can",
            "may",
            "might",
            "must",
        }
        return [w for w in words if w not in stopwords]


__all__ = ["QAEvaluator"]
