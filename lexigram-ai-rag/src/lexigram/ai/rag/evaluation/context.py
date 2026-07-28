"""Context relevance evaluation metrics."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.rag.evaluation.base import EvaluatorBase
from lexigram.ai.rag.evaluation.types import EvaluationResult, MetricType
from lexigram.contracts import ChatMessage
from lexigram.di.decorators import inject
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.contracts.ai import LLMClientProtocol

logger = get_logger(__name__)


@inject
class ContextRelevanceEvaluator(EvaluatorBase):
    """Evaluates context relevance using LLM-as-judge.

    Measures how relevant the retrieved context is to the query.
    """

    def __init__(self, llm_client: LLMClientProtocol):
        """Initialize context relevance evaluator.

        Args:
            llm_client: LLM client for evaluation.
        """
        super().__init__("context_relevance")
        self.llm_client = llm_client

    async def evaluate(
        self,
        query: str,
        retrieved_docs: list[Any],
        generated_answer: str,
        reference_answer: str | None = None,
        **kwargs,
    ) -> EvaluationResult:
        """Evaluate context relevance.

        Args:
            query: The query.
            retrieved_docs: Retrieved documents to evaluate.
            generated_answer: Generated answer (not used).
            reference_answer: Not used.
            **kwargs: Additional parameters.

        Returns:
            Context relevance score.
        """
        if not retrieved_docs:
            return EvaluationResult(
                metric_type=MetricType.CONTEXT_RELEVANCE,
                score=0.0,
                details={"reason": "No documents retrieved"},
            )

        # Build context
        context_parts = []
        for i, doc in enumerate(retrieved_docs):
            if isinstance(doc, dict):
                content = doc.get("content", str(doc))
            elif hasattr(doc, "content"):
                content = doc.content
            else:
                content = str(doc)
            context_parts.append(f"[{i + 1}] {content}")

        context_str = "\n".join(context_parts)

        prompt = f"""Evaluate how relevant the retrieved context is to answering the query.
Score from 0.0 (completely irrelevant) to 1.0 (perfectly relevant).

Query: {query}

Retrieved Context:
{context_str}

Provide only a number between 0.0 and 1.0 as your response."""

        try:
            result = await self.llm_client.complete(
                messages=[ChatMessage(role="user", content=prompt)]
            )
            if result.is_err():
                raise result.unwrap_err()
            response = result.unwrap()
            score_text = response.content.strip()
            score = float(score_text)
            score = max(0.0, min(1.0, score))

            return EvaluationResult(
                metric_type=MetricType.CONTEXT_RELEVANCE,
                score=score,
                details={
                    "llm_response": score_text,
                    "context_chunks": len(retrieved_docs),
                },
            )
        except Exception as e:
            logger.exception("Error computing evaluation metric")
            return EvaluationResult(
                metric_type=MetricType.CONTEXT_RELEVANCE,
                score=0.0,
                details={"error": str(e)},
            )
