"""Base evaluator class for RAG evaluation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from lexigram.ai.rag.evaluation.types import EvaluationResult


class EvaluatorBase(ABC):
    """Base class for RAG evaluators.

    All evaluators should inherit from this class and implement the evaluate method.
    """

    def __init__(self, name: str = "base"):
        """Initialize evaluator.

        Args:
            name: Name of the evaluator.
        """
        self.name = name

    @abstractmethod
    async def evaluate(
        self,
        query: str,
        retrieved_docs: list[Any],
        generated_answer: str,
        reference_answer: str | None = None,
        **kwargs,
    ) -> EvaluationResult:
        """Evaluate a RAG response.

        Args:
            query: The query.
            retrieved_docs: Retrieved documents.
            generated_answer: Generated answer.
            reference_answer: Optional ground truth.
            **kwargs: Additional parameters.

        Returns:
            Evaluation result.
        """
