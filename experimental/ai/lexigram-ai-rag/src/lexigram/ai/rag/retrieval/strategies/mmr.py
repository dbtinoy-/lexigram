"""Maximal Marginal Relevance (MMR) retrieval strategy."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.ai.vector import SearchResultProtocol

__all__ = ["MMRRetrievalStrategy"]


class MMRRetrievalStrategy:
    """Maximal Marginal Relevance retrieval.

    Balances relevance to the query with diversity among the selected documents
    by using pre-computed similarity scores as a relevance proxy.

    Reference: Carbonell & Goldstein (1998) — The Use of MMR for
    Diversity-Based Reranking of Documents and Query Terms.
    """

    def __init__(self, lambda_param: float = 0.5) -> None:
        """Initialise the MMR strategy.

        Args:
            lambda_param: Trade-off between relevance (1.0) and diversity (0.0).
                          Default 0.5 balances both equally.
        """
        self._lambda = lambda_param

    async def retrieve(
        self,
        query: str,
        candidates: list[SearchResultProtocol],
        *,
        top_k: int = 5,
        **kwargs: Any,
    ) -> list[SearchResultProtocol]:
        """Retrieve top-k candidates using MMR diversification.

        Uses pre-computed similarity scores as a relevance proxy. Redundancy
        between candidates is estimated as the inverse of their absolute score
        difference — candidates with very similar scores are treated as more
        likely to be redundant.

        Args:
            query: The user query.
            candidates: Search result candidates with similarity scores.
            top_k: Maximum number of results to return.
            **kwargs: Ignored additional options.

        Returns:
            Diversified top-k candidates.
        """
        if not candidates:
            return []

        effective_k = min(top_k, len(candidates))
        remaining = sorted(candidates, key=lambda c: c.score, reverse=True)
        selected: list[SearchResultProtocol] = []

        # Seed with the most relevant candidate.
        selected.append(remaining.pop(0))

        while len(selected) < effective_k and remaining:
            best_candidate = None
            best_mmr_score = float("-inf")

            for candidate in remaining:
                relevance = candidate.score
                # Proxy redundancy: 1 minus absolute score difference.
                max_sim_to_selected = max(
                    1.0 - abs(candidate.score - s.score) for s in selected
                )
                mmr_score = (
                    self._lambda * relevance
                    - (1.0 - self._lambda) * max_sim_to_selected
                )
                if mmr_score > best_mmr_score:
                    best_mmr_score = mmr_score
                    best_candidate = candidate

            if best_candidate is not None:
                selected.append(best_candidate)
                remaining.remove(best_candidate)

        return selected
