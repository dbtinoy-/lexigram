"""Context ranker for synthesis.

This module implements context ranking to reorder chunks by relevance
before synthesis.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.contracts.ai import EmbeddingClientProtocol

from lexigram.ai.rag.synthesis.types import ContextChunk


class ContextRanker:
    """Rank context chunks by relevance.

    This component reorders chunks to prioritize the most relevant content
    for synthesis.

    Attributes:
        embedding_client: Optional embedding client for semantic ranking
        use_scores: Whether to use existing chunk scores
        use_recency: Whether to consider recency (if available in metadata)
    """

    def __init__(
        self,
        embedding_client: EmbeddingClientProtocol | None = None,
        use_scores: bool = True,
        use_recency: bool = False,
    ):
        """Initialize the context ranker.

        Args:
            embedding_client: Optional embedding client
            use_scores: Whether to use chunk scores
            use_recency: Whether to consider recency
        """
        self.embedding_client = embedding_client
        self.use_scores = use_scores
        self.use_recency = use_recency

    async def rank_chunks(
        self,
        query: str,
        chunks: list[ContextChunk],
    ) -> list[ContextChunk]:
        """Rank chunks by relevance to query.

        Args:
            query: The user query
            chunks: Chunks to rank

        Returns:
            Ranked list of chunks
        """
        if not chunks:
            return []

        # If using existing scores, just sort by score
        if self.use_scores and all(
            chunk.score is not None and chunk.score > 0 for chunk in chunks
        ):
            ranked = sorted(
                chunks,
                key=lambda c: c.score if c.score is not None else 0.0,
                reverse=True,
            )

            # Update ranks
            for i, chunk in enumerate(ranked):
                object.__setattr__(chunk, "rank", i)

            return ranked

        # Otherwise, use simple ranking
        # For now, preserve original order and set ranks
        for i, chunk in enumerate(chunks):
            object.__setattr__(chunk, "rank", i)

        return chunks

    async def rerank_chunks(
        self,
        query: str,
        chunks: list[ContextChunk],
        top_k: int | None = None,
    ) -> list[ContextChunk]:
        """Rerank chunks and optionally limit to top K.

        Args:
            query: The user query
            chunks: Chunks to rerank
            top_k: Number of top chunks to return (None = all)

        Returns:
            Reranked and filtered chunks
        """
        ranked = await self.rank_chunks(query, chunks)

        if top_k:
            return ranked[:top_k]

        return ranked
