"""Hallucination detection evaluation metrics."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.rag.evaluation.base import EvaluatorBase
from lexigram.ai.rag.evaluation.types import EvaluationResult, MetricType
from lexigram.contracts import ChatMessage
from lexigram.di.decorators import inject

if TYPE_CHECKING:
    from lexigram.contracts.ai import LLMClientProtocol


@inject
class HallucinationDetector(EvaluatorBase):
    """Detects hallucinations in generated answers.

    Uses LLM to identify claims in the answer and verify them against context.
    """

    def __init__(self, llm_client: LLMClientProtocol):
        """Initialize hallucination detector.

        Args:
            llm_client: LLM client for detection.
        """
        super().__init__("hallucination_detector")
        self.llm_client = llm_client

    async def evaluate(
        self,
        query: str,
        retrieved_docs: list[Any],
        generated_answer: str,
        reference_answer: str | None = None,
        **kwargs,
    ) -> EvaluationResult:
        """Detect hallucinations.

        Args:
            query: The query.
            retrieved_docs: Retrieved documents for verification.
            generated_answer: Generated answer to check.
            reference_answer: Not used.
            **kwargs: Additional parameters.

        Returns:
            Hallucination rate (0.0 = no hallucinations, 1.0 = all hallucinated).
        """
        # Build context
        context_parts = []
        for doc in retrieved_docs:
            if isinstance(doc, dict):
                content = doc.get("content", str(doc))
            elif hasattr(doc, "content"):
                content = doc.content
            else:
                content = str(doc)
            context_parts.append(content)

        context_str = "\n".join(context_parts)

        prompt = f"""Analyze the answer and identify any claims that are NOT supported by the context.

Context:
{context_str}

Answer: {generated_answer}

For each claim in the answer, check if it's supported by the context.
Provide a hallucination rate from 0.0 (all claims supported) to 1.0 (all claims unsupported).
Provide only a number between 0.0 and 1.0 as your response."""

        try:
            result = await self.llm_client.complete(
                messages=[ChatMessage(role="user", content=prompt)]
            )
            if result.is_err():
                raise result.unwrap_err()
            response = result.unwrap()
            score_text = response.content.strip()
            hallucination_rate = float(score_text)
            hallucination_rate = max(0.0, min(1.0, hallucination_rate))

            return EvaluationResult(
                metric_type=MetricType.HALLUCINATION_RATE,
                score=hallucination_rate,
                details={"llm_response": score_text},
            )
        except (ConnectionError, TimeoutError, RuntimeError, ValueError, OSError) as e:
            return EvaluationResult(
                metric_type=MetricType.HALLUCINATION_RATE,
                score=1.0,  # Assume worst case on error
                details={"error": str(e)},
            )
