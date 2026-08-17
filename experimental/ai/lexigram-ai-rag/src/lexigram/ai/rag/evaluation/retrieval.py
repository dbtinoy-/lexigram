"""Retrieval-based evaluation metrics."""

from __future__ import annotations

from typing import Any

from lexigram.ai.rag.evaluation.base import EvaluatorBase
from lexigram.ai.rag.evaluation.types import EvaluationResult, MetricType


class RetrievalPrecisionEvaluator(EvaluatorBase):
    """Evaluates retrieval precision.

    Measures the fraction of retrieved documents that are relevant.
    Requires ground truth relevant document IDs.
    """

    def __init__(self) -> None:
        """Initialize retrieval precision evaluator."""
        super().__init__("retrieval_precision")

    async def evaluate(
        self,
        query: str,
        retrieved_docs: list[Any],
        generated_answer: str,
        reference_answer: str | None = None,
        **kwargs,
    ) -> EvaluationResult:
        """Evaluate retrieval precision.

        Args:
            query: The query.
            retrieved_docs: Retrieved documents (should have 'id' or be IDs).
            generated_answer: Generated answer (not used).
            reference_answer: Not used.
            **kwargs: Must contain 'relevant_doc_ids' (set of relevant IDs).

        Returns:
            Precision score.
        """
        relevant_doc_ids = kwargs.get("relevant_doc_ids", set())

        if not retrieved_docs:
            return EvaluationResult(
                metric_type=MetricType.RETRIEVAL_PRECISION,
                score=0.0,
                details={"reason": "No documents retrieved"},
            )

        # Extract IDs from retrieved docs
        retrieved_ids = set()
        for doc in retrieved_docs:
            if isinstance(doc, dict):
                retrieved_ids.add(doc.get("id", doc.get("doc_id")))
            elif hasattr(doc, "id"):
                retrieved_ids.add(doc.id)
            else:
                retrieved_ids.add(str(doc))

        # Calculate precision
        if not retrieved_ids:
            precision = 0.0
        else:
            relevant_retrieved = retrieved_ids & relevant_doc_ids
            precision = len(relevant_retrieved) / len(retrieved_ids)

        return EvaluationResult(
            metric_type=MetricType.RETRIEVAL_PRECISION,
            score=precision,
            details={
                "retrieved_count": len(retrieved_ids),
                "relevant_count": len(relevant_doc_ids),
                "relevant_retrieved": len(retrieved_ids & relevant_doc_ids),
            },
        )


class RetrievalRecallEvaluator(EvaluatorBase):
    """Evaluates retrieval recall.

    Measures the fraction of relevant documents that were retrieved.
    Requires ground truth relevant document IDs.
    """

    def __init__(self) -> None:
        """Initialize retrieval recall evaluator."""
        super().__init__("retrieval_recall")

    async def evaluate(
        self,
        query: str,
        retrieved_docs: list[Any],
        generated_answer: str,
        reference_answer: str | None = None,
        **kwargs,
    ) -> EvaluationResult:
        """Evaluate retrieval recall.

        Args:
            query: The query.
            retrieved_docs: Retrieved documents.
            generated_answer: Generated answer (not used).
            reference_answer: Not used.
            **kwargs: Must contain 'relevant_doc_ids'.

        Returns:
            Recall score.
        """
        relevant_doc_ids = kwargs.get("relevant_doc_ids", set())

        if not relevant_doc_ids:
            return EvaluationResult(
                metric_type=MetricType.RETRIEVAL_RECALL,
                score=0.0,
                details={"reason": "No relevant documents specified"},
            )

        # Extract IDs
        retrieved_ids = set()
        for doc in retrieved_docs:
            if isinstance(doc, dict):
                retrieved_ids.add(doc.get("id", doc.get("doc_id")))
            elif hasattr(doc, "id"):
                retrieved_ids.add(doc.id)
            else:
                retrieved_ids.add(str(doc))

        # Calculate recall
        relevant_retrieved = retrieved_ids & relevant_doc_ids
        recall = len(relevant_retrieved) / len(relevant_doc_ids)

        return EvaluationResult(
            metric_type=MetricType.RETRIEVAL_RECALL,
            score=recall,
            details={
                "retrieved_count": len(retrieved_ids),
                "relevant_count": len(relevant_doc_ids),
                "relevant_retrieved": len(relevant_retrieved),
            },
        )
