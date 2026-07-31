"""Dynamic few-shot example selector using embedding similarity.

Uses cosine similarity between query embeddings and example embeddings to
select the most semantically relevant examples from a pool — as opposed to
static, hand-picked few-shot examples.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.ai.prompt.optimization.types import Example
    from lexigram.contracts.ai import EmbeddingClientProtocol

logger = get_logger(__name__)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two equal-length vectors.

    Args:
        a: First embedding vector.
        b: Second embedding vector.

    Returns:
        Cosine similarity value in [-1, 1].
    """
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


class DynamicFewShotSelector:
    """Select the most relevant few-shot examples for a given query.

    Uses embedding cosine similarity to rank a pool of labelled examples
    against the incoming query, returning the top-*k* most relevant ones.
    Pre-computes example embeddings on first use (lazy cache).

    Example::

        selector = DynamicFewShotSelector(
            examples=training_examples,
            embedding_client=openai_client,
            max_examples=3,
        )
        best = await selector.select("What is the capital of France?")
    """

    def __init__(
        self,
        examples: list[Example],
        embedding_client: EmbeddingClientProtocol,
        *,
        max_examples: int = 3,
    ) -> None:
        """Initialize the few-shot selector.

        Args:
            examples: Pool of labelled examples to select from.
            embedding_client: Client used to generate embeddings.
            max_examples: Maximum number of examples to return per query.
        """
        self._examples = examples
        self._embedding_client = embedding_client
        self._max_examples = max_examples
        self._example_embeddings: list[list[float]] | None = None

    async def _ensure_embeddings(self) -> None:
        """Lazily compute and cache embeddings for the example pool."""
        if self._example_embeddings is not None:
            return

        logger.debug(
            "few_shot_selector_computing_embeddings",
            example_count=len(self._examples),
        )
        texts = [ex.input for ex in self._examples]
        self._example_embeddings = await self._embedding_client.embed(texts)

    async def select(self, query: str) -> list[Example]:
        """Return the top-*k* examples most similar to *query*.

        Args:
            query: The input query to find relevant examples for.

        Returns:
            List of up to ``max_examples`` examples ordered by descending
            similarity.
        """
        if not self._examples:
            return []

        await self._ensure_embeddings()
        assert self._example_embeddings is not None  # noqa: S101  # post-condition

        query_embedding = await self._embedding_client.embed([query])
        q_vec = query_embedding[0]

        scored: list[tuple[float, Example]] = [
            (_cosine_similarity(q_vec, ex_vec), ex)
            for ex_vec, ex in zip(self._example_embeddings, self._examples, strict=True)
        ]
        scored.sort(key=lambda t: t[0], reverse=True)

        top = [ex for _, ex in scored[: self._max_examples]]
        logger.debug(
            "few_shot_selector_selected",
            selected_count=len(top),
            top_score=scored[0][0] if scored else 0.0,
        )
        return top

    def invalidate_cache(self) -> None:
        """Clear the cached example embeddings (e.g. after pool update)."""
        self._example_embeddings = None


__all__ = ["DynamicFewShotSelector"]
