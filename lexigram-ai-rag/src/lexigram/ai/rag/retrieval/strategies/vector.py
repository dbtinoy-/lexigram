"""Simple vector similarity retrieval strategy."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.ai.vector import SearchResultProtocol

__all__ = ["VectorRetrievalStrategy"]


class VectorRetrievalStrategy:
    """Simple vector similarity retrieval.

    Re-ranks candidates by their pre-computed similarity score and returns the
    top-k results. No additional embedding computation is required.
    """

    async def retrieve(
        self,
        query: str,
        candidates: list[SearchResultProtocol],
        *,
        top_k: int = 5,
        **kwargs: Any,
    ) -> list[SearchResultProtocol]:
        """Retrieve top-k candidates by similarity score.

        Args:
            query: The user query (unused — scores are pre-computed).
            candidates: Search results with pre-computed similarity scores.
            top_k: Maximum number of results to return.
            **kwargs: Ignored additional options.

        Returns:
            Top-k candidates sorted by score descending.
        """
        sorted_candidates = sorted(candidates, key=lambda c: c.score, reverse=True)
        return sorted_candidates[:top_k]
