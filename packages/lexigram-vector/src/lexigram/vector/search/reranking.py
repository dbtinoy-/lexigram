"""Reranking for improving search result quality.

This module provides reranking capabilities to improve the quality of search results
by re-scoring and re-ordering them based on various strategies.

Example:
    >>> from lexigram.contracts.ai.vector import Document, RAGSearchResult
    >>> from lexigram.vector.search.reranking import SimilarityReranker
    >>>
    >>> reranker = SimilarityReranker()
    >>> results = await reranker.rerank(query="python", results=search_results)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from lexigram.domain.models.base import DomainModel
from lexigram.validation import Field
from lexigram.vector.search.rerankers import (
    CrossEncoderReranker as CrossEncoderReranker,
)
from lexigram.vector.search.rerankers import CustomReranker as CustomReranker
from lexigram.vector.search.rerankers import DiversityReranker as DiversityReranker
from lexigram.vector.search.rerankers import SearchResult as SearchResult
from lexigram.vector.search.rerankers import SimilarityReranker as SimilarityReranker

__all__ = [
    "CrossEncoderReranker",
    "CustomReranker",
    "DiversityReranker",
    "Reranker",
    "RerankerPipeline",
    "RerankingConfig",
    "RerankingStrategy",
    "SimilarityReranker",
    "create_reranker",
]


class RerankingStrategy(StrEnum):
    """Reranking strategy types."""

    SIMILARITY = "similarity"  # Similarity-based scoring
    CROSS_ENCODER = "cross_encoder"  # Cross-encoder model
    DIVERSITY = "diversity"  # Maximize diversity
    CUSTOM = "custom"  # Custom scoring function


class Reranker(Protocol):
    """Protocol for reranking search results.

    Rerankers take an initial list of search results and re-order them
    to improve relevance based on various strategies.
    """

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int | None = None,
    ) -> list[SearchResult]:
        """Rerank search results.

        Args:
            query: Original search query
            results: Initial search results
            top_k: Number of top results to return (None = all)

        Returns:
            Reranked search results
        """
        ...


@dataclass(init=False)
class RerankingConfig(DomainModel):
    """Configuration for reranking.

    Example:
        >>> config = RerankingConfig(
        ...     strategy=RerankingStrategy.SIMILARITY,
        ...     score_boost=0.15,
        ...     top_k=10
        ... )
    """

    strategy: RerankingStrategy = Field(
        default=RerankingStrategy.SIMILARITY,
        description="Reranking strategy to use",
    )
    score_boost: float = Field(
        default=0.1,
        ge=0.0,
        description="Score boost for term matches (similarity strategy)",
    )
    exact_match_boost: float = Field(
        default=0.5,
        ge=0.0,
        description="Boost for exact matches (similarity strategy)",
    )
    lambda_param: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Relevance vs diversity trade-off (diversity strategy)",
    )
    top_k: int | None = Field(
        default=None,
        ge=1,
        description="Number of top results to return",
    )


def create_reranker(
    strategy: RerankingStrategy = RerankingStrategy.SIMILARITY,
    config: RerankingConfig | None = None,
    **kwargs: Any,
) -> Reranker:
    """Create a reranker based on strategy.

    Args:
        strategy: Reranking strategy
        config: Optional configuration
        **kwargs: Additional arguments for specific rerankers

    Returns:
        Configured reranker

    Example:
        >>> reranker = create_reranker(RerankingStrategy.SIMILARITY)
        >>> results = await reranker.rerank("query", search_results)
    """
    config = config or RerankingConfig()

    if strategy == RerankingStrategy.SIMILARITY:
        return SimilarityReranker(
            score_boost=kwargs.get("score_boost", config.score_boost),
            exact_match_boost=kwargs.get("exact_match_boost", config.exact_match_boost),
        )
    if strategy == RerankingStrategy.DIVERSITY:
        return DiversityReranker(
            lambda_param=kwargs.get("lambda_param", config.lambda_param),
        )
    if strategy == RerankingStrategy.CUSTOM:
        score_fn = kwargs.get("score_fn")
        if score_fn is None:
            msg = "Custom reranker requires 'score_fn' argument"
            raise ValueError(msg)
        return CustomReranker(score_fn=score_fn)
    if strategy == RerankingStrategy.CROSS_ENCODER:
        raise NotImplementedError(
            "Cross-encoder reranking is not supported in the current version.",
        )
    raise ValueError(f"Unknown reranking strategy: {strategy}")


class RerankerPipeline:
    """Pipeline for applying multiple rerankers in sequence.

    Example:
        >>> pipeline = RerankerPipeline([
        ...     SimilarityReranker(),
        ...     DiversityReranker()
        ... ])
        >>> results = await pipeline.rerank("python", search_results)
    """

    def __init__(self, rerankers: list[Reranker]):
        """Initialize reranker pipeline.

        Args:
            rerankers: List of rerankers to apply in sequence
        """
        self.rerankers = rerankers

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int | None = None,
    ) -> list[SearchResult]:
        """Apply all rerankers in sequence.

        Args:
            query: Search query
            results: Initial results
            top_k: Number of final results to return

        Returns:
            Reranked results after all stages
        """
        current_results = results

        for reranker in self.rerankers:
            current_results = await reranker.rerank(query, current_results)

        if top_k is not None:
            current_results = current_results[:top_k]

        return current_results
