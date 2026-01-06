"""Protocol for reranking strategies."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from lexigram.ai.rag.reranking.types import RerankResult


@runtime_checkable
class RerankerProtocol(Protocol):
    """Protocol for document reranking strategies.

    Reranking strategies reorder documents by relevance using specialized
    models or heuristics.
    """

    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int | None = None,
        **kwargs,
    ) -> RerankResult:
        """Rerank documents by relevance to the query.

        Args:
            query: The query string.
            documents: List of documents to rerank.
            top_k: Return only top k documents. None = return all.
            **kwargs: Additional strategy-specific parameters.

        Returns:
            RerankResult with reranked documents and scores.
        """
        ...
