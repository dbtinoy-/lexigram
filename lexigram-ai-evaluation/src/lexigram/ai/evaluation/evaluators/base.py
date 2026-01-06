"""Base evaluator class."""

from __future__ import annotations

from lexigram.contracts.ai.evaluation import EvaluationResult, EvaluationScoreType
from lexigram.logging import get_logger

logger = get_logger(__name__)


class BaseEvaluator:
    """Base class for evaluators."""

    def __init__(self, score_type: EvaluationScoreType) -> None:
        self._score_type = score_type

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def _create_result(
        self,
        score: float,
        feedback: str,
        metrics: dict[str, float | str] | None = None,
    ) -> EvaluationResult:
        return EvaluationResult(
            score=score,
            score_type=self._score_type,
            feedback=feedback,
            metrics=metrics or {},
        )


__all__ = ["BaseEvaluator"]
