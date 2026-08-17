"""Main RAG evaluation orchestrator."""

from __future__ import annotations

from typing import Any

from lexigram.ai.rag.evaluation.base import EvaluatorBase
from lexigram.ai.rag.evaluation.types import (
    EvaluationResult,
    MetricType,
    RAGEvaluationReport,
)


class RAGEvaluator:
    """Comprehensive RAG evaluation orchestrator.

    Coordinates multiple evaluators to produce a complete evaluation report.
    """

    def __init__(
        self,
        evaluators: list[EvaluatorBase] | None = None,
        weights: dict[MetricType, float] | None = None,
    ):
        """Initialize RAG evaluator.

        Args:
            evaluators: List of evaluators to use.
            weights: Optional weights for computing overall score.
        """
        self.evaluators = evaluators or []
        self.weights = weights or {}

    def add_evaluator(self, evaluator: EvaluatorBase) -> Any:
        """Add an evaluator.

        Args:
            evaluator: Evaluator to add.
        """
        self.evaluators.append(evaluator)

    async def evaluate(
        self,
        query: str,
        retrieved_docs: list[Any],
        generated_answer: str,
        reference_answer: str | None = None,
        **kwargs,
    ) -> RAGEvaluationReport:
        """Run all evaluators and produce a report.

        Args:
            query: The query.
            retrieved_docs: Retrieved documents.
            generated_answer: Generated answer.
            reference_answer: Optional ground truth.
            **kwargs: Additional parameters for evaluators.

        Returns:
            Complete evaluation report.
        """
        results = []

        # Run all evaluators
        for evaluator in self.evaluators:
            result = await evaluator.evaluate(
                query=query,
                retrieved_docs=retrieved_docs,
                generated_answer=generated_answer,
                reference_answer=reference_answer,
                **kwargs,
            )
            results.append(result)

        # Calculate overall score
        overall_score = self._calculate_overall_score(results)

        return RAGEvaluationReport(
            query=query,
            retrieved_docs=retrieved_docs,
            generated_answer=generated_answer,
            reference_answer=reference_answer,
            results=results,
            overall_score=overall_score,
            metadata=kwargs.get("metadata", {}),
        )

    def _calculate_overall_score(self, results: list[EvaluationResult]) -> float:
        """Calculate weighted overall score.

        Args:
            results: Individual evaluation results.

        Returns:
            Overall score (0.0 to 1.0).
        """
        if not results:
            return 0.0

        # If no weights specified, use equal weights
        if not self.weights:
            # Invert hallucination rate (lower is better)
            total = 0.0
            count = 0
            for result in results:
                if result.metric_type == MetricType.HALLUCINATION_RATE:
                    total += 1.0 - result.score  # Invert
                else:
                    total += result.score
                count += 1
            return total / count if count > 0 else 0.0

        # Use weighted average
        weighted_sum = 0.0
        total_weight = 0.0

        for result in results:
            weight = self.weights.get(result.metric_type, 0.0)
            if weight > 0:
                score = result.score
                # Invert hallucination rate
                if result.metric_type == MetricType.HALLUCINATION_RATE:
                    score = 1.0 - score
                weighted_sum += score * weight
                total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0
