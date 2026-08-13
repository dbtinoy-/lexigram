"""Answer quality evaluation metrics."""

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
class AnswerRelevanceEvaluator(EvaluatorBase):
    """Evaluates answer relevance using LLM-as-judge.

    Measures how well the answer addresses the query.
    """

    def __init__(self, llm_client: LLMClientProtocol):
        """Initialize answer relevance evaluator.

        Args:
            llm_client: LLM client for evaluation.
        """
        super().__init__("answer_relevance")
        self.llm_client = llm_client

    async def evaluate(
        self,
        query: str,
        retrieved_docs: list[Any],
        generated_answer: str,
        reference_answer: str | None = None,
        **kwargs,
    ) -> EvaluationResult:
        """Evaluate answer relevance.

        Args:
            query: The query.
            retrieved_docs: Retrieved documents (not used).
            generated_answer: Generated answer to evaluate.
            reference_answer: Not used.
            **kwargs: Additional parameters.

        Returns:
            Relevance score.
        """
        prompt = f"""Evaluate how relevant the following answer is to the query.
Score from 0.0 (completely irrelevant) to 1.0 (perfectly relevant).

Query: {query}

Answer: {generated_answer}

Provide only a number between 0.0 and 1.0 as your response."""

        try:
            result = await self.llm_client.complete(
                messages=[ChatMessage(role="user", content=prompt)]
            )
            if result.is_err():
                raise result.unwrap_err()
            response = result.unwrap()
            # Extract score from response
            score_text = response.content.strip()
            score = float(score_text)
            score = max(0.0, min(1.0, score))  # Clamp to [0, 1]

            return EvaluationResult(
                metric_type=MetricType.ANSWER_RELEVANCE,
                score=score,
                details={"llm_response": score_text},
            )
        except Exception as e:
            logger.exception("Error computing evaluation metric")
            return EvaluationResult(
                metric_type=MetricType.ANSWER_RELEVANCE,
                score=0.0,
                details={"error": str(e)},
            )


@inject
class AnswerFaithfulnessEvaluator(EvaluatorBase):
    """Evaluates answer faithfulness using LLM-as-judge.

    Measures whether the answer is grounded in the retrieved context
    (i.e., not hallucinated).
    """

    def __init__(self, llm_client: LLMClientProtocol):
        """Initialize answer faithfulness evaluator.

        Args:
            llm_client: LLM client for evaluation.
        """
        super().__init__("answer_faithfulness")
        self.llm_client = llm_client

    async def evaluate(
        self,
        query: str,
        retrieved_docs: list[Any],
        generated_answer: str,
        reference_answer: str | None = None,
        **kwargs,
    ) -> EvaluationResult:
        """Evaluate answer faithfulness.

        Args:
            query: The query.
            retrieved_docs: Retrieved documents to check against.
            generated_answer: Generated answer to evaluate.
            reference_answer: Not used.
            **kwargs: Additional parameters.

        Returns:
            Faithfulness score.
        """
        # Build context from retrieved docs
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

        prompt = f"""Evaluate whether the answer is faithful to the provided context.
Score from 0.0 (completely unfaithful/hallucinated) to 1.0 (perfectly faithful).

Context:
{context_str}

Answer: {generated_answer}

The answer should only contain information that can be verified from the context.
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
                metric_type=MetricType.ANSWER_FAITHFULNESS,
                score=score,
                details={
                    "llm_response": score_text,
                    "context_chunks": len(retrieved_docs),
                },
            )
        except Exception as e:
            logger.exception("Error computing evaluation metric")
            return EvaluationResult(
                metric_type=MetricType.ANSWER_FAITHFULNESS,
                score=0.0,
                details={"error": str(e)},
            )
