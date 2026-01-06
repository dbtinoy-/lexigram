"""Convenience function for RAG evaluation."""

from __future__ import annotations

from typing import Any

from lexigram.ai.rag.evaluation.answer import (
    AnswerFaithfulnessEvaluator,
    AnswerRelevanceEvaluator,
)
from lexigram.ai.rag.evaluation.base import EvaluatorBase
from lexigram.ai.rag.evaluation.context import ContextRelevanceEvaluator
from lexigram.ai.rag.evaluation.evaluator import RAGEvaluator
from lexigram.ai.rag.evaluation.hallucination import HallucinationDetector
from lexigram.ai.rag.evaluation.retrieval import (
    RetrievalPrecisionEvaluator,
    RetrievalRecallEvaluator,
)
from lexigram.ai.rag.evaluation.types import RAGEvaluationReport


async def evaluate_rag(
    query: str,
    retrieved_docs: list[Any],
    generated_answer: str,
    reference_answer: str | None = None,
    llm_client: Any = None,
    evaluators: list[EvaluatorBase] | None = None,
    **kwargs: Any,
) -> RAGEvaluationReport:
    """Convenience function for RAG evaluation.

    Args:
        query: The query.
        retrieved_docs: Retrieved documents.
        generated_answer: Generated answer.
        reference_answer: Optional ground truth.
        llm_client: Optional LLM client for LLM-based metrics.
        evaluators: Optional custom evaluators.
        **kwargs: Additional parameters.

    Returns:
        Evaluation report.
    """
    if evaluators is None:
        evaluators = []

        # Add basic retrieval metrics if relevant docs provided
        if "relevant_doc_ids" in kwargs:
            evaluators.append(RetrievalPrecisionEvaluator())
            evaluators.append(RetrievalRecallEvaluator())

        # Add LLM-based metrics if LLM client provided
        if llm_client is not None:
            evaluators.append(AnswerRelevanceEvaluator(llm_client))
            evaluators.append(AnswerFaithfulnessEvaluator(llm_client))
            evaluators.append(ContextRelevanceEvaluator(llm_client))
            evaluators.append(HallucinationDetector(llm_client))

    evaluator = RAGEvaluator(evaluators=evaluators)
    return await evaluator.evaluate(
        query=query,
        retrieved_docs=retrieved_docs,
        generated_answer=generated_answer,
        reference_answer=reference_answer,
        **kwargs,
    )
