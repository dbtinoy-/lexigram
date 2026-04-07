"""Embedding-based distance evaluator."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.ai.evaluation.evaluators.base import BaseEvaluator
from lexigram.contracts.ai.evaluation import (
    EvaluationResult,
    EvaluationScoreType,
    EvaluatorProtocol,
)
from lexigram.logging import get_logger
from lexigram.result import Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.ai.llm import EmbeddingClientProtocol

logger = get_logger(__name__)


class EmbeddingDistanceEvaluator(BaseEvaluator, EvaluatorProtocol):
    """Embedding-based similarity evaluation.

    Evaluates output against reference using embedding similarity.
    Requires an EmbeddingClientProtocol to be available in the container.
    """

    def __init__(
        self,
        embedding_client: EmbeddingClientProtocol | None = None,
    ) -> None:
        super().__init__(EvaluationScoreType.SEMANTIC_SIMILARITY)
        self._embedding_client = embedding_client

    @property
    def name(self) -> str:
        return "embedding_distance"

    def set_embedding_client(
        self,
        client: EmbeddingClientProtocol,
    ) -> None:
        self._embedding_client = client

    async def evaluate(
        self,
        input: str,
        output: str,
        reference: str,
    ) -> Result[EvaluationResult, Exception]:
        if self._embedding_client is None:
            return Ok(
                self._create_result(
                    0.0,
                    "No embedding client configured",
                    {"error": "embedding_client_not_available"},
                )
            )

        try:
            emb_output = await self._embedding_client.embed([output])
            emb_ref = await self._embedding_client.embed([reference])

            emb_out_list: list[list[float]] = (
                emb_output
                if isinstance(emb_output, list)
                else getattr(emb_output, "embeddings", emb_output)
            )
            emb_ref_list: list[list[float]] = (
                emb_ref
                if isinstance(emb_ref, list)
                else getattr(emb_ref, "embeddings", emb_ref)
            )

            if not emb_out_list or not emb_ref_list:
                return Ok(
                    self._create_result(
                        0.0,
                        "Failed to compute embeddings",
                        {"error": "embedding_computation_failed"},
                    )
                )

            similarity = self._cosine_similarity(
                emb_out_list[0],
                emb_ref_list[0],
            )

            return Ok(
                self._create_result(
                    similarity,
                    f"Semantic similarity: {similarity:.2f}",
                    {"similarity": similarity},
                )
            )
        except Exception as e:
            logger.error("embedding_evaluation_failed", error=str(e))
            return Ok(
                self._create_result(
                    0.0,
                    f"Evaluation failed: {e}",
                    {"error": str(e)},
                )
            )

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        dot_product: float = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a: float = sum(x * x for x in a) ** 0.5
        norm_b: float = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)


__all__ = ["EmbeddingDistanceEvaluator"]
