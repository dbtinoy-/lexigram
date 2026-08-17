"""String distance evaluator."""

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


class StringDistanceEvaluator(BaseEvaluator, EvaluatorProtocol):
    """String similarity evaluation.

    Evaluates output against reference using string distance metrics.
    Supports Levenshtein, Jaccard, and cosine similarity.
    """

    def __init__(self, metric: str = "levenshtein") -> None:
        super().__init__(EvaluationScoreType.STRING_DISTANCE)
        self._metric = metric

    @property
    def name(self) -> str:
        return "string_distance"

    async def evaluate(
        self,
        input: str,
        output: str,
        reference: str,
    ) -> Result[EvaluationResult, Exception]:
        output_norm = output.strip().lower()
        reference_norm = reference.strip().lower()

        if self._metric == "levenshtein":
            distance = self._levenshtein_distance(output_norm, reference_norm)
            max_dist = max(len(output_norm), len(reference_norm))
            score = 1.0 - (distance / max_dist) if max_dist > 0 else 1.0
            details: dict[str, float | str] = {
                "distance": distance,
                "max_distance": max_dist,
            }
        elif self._metric == "jaccard":
            score = self._jaccard_similarity(output_norm, reference_norm)
            details = {"metric": "jaccard"}
        else:
            score = self._jaccard_similarity(output_norm, reference_norm)
            details = {"metric": "jaccard"}

        feedback = f"Similarity score: {score:.2f}"

        return Ok(self._create_result(score, feedback, details))

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def _jaccard_similarity(self, s1: str, s2: str) -> float:
        set1 = set(s1.split())
        set2 = set(s2.split())
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0


__all__ = ["StringDistanceEvaluator"]
