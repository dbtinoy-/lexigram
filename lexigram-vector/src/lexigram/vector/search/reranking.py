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

from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any, Protocol

from lexigram.contracts.ai.vector import Document, RAGSearchResult
from lexigram.domain.models.base import DomainModel
from lexigram.validation import Field

SearchResult = RAGSearchResult

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


class SimilarityReranker:
    """Similarity-based reranking.

    Reranks results based on text similarity between query and documents.
    Uses simple scoring strategies suitable for the community edition.

    Example:
        >>> reranker = SimilarityReranker(score_boost=0.1)
        >>> results = await reranker.rerank("python programming", search_results)
    """

    def __init__(
        self,
        score_boost: float = 0.1,
        exact_match_boost: float = 0.5,
        case_sensitive: bool = False,
    ):
        """Initialize similarity reranker.

        Args:
            score_boost: Score boost for term matches (default: 0.1)
            exact_match_boost: Additional boost for exact matches (default: 0.5)
            case_sensitive: Whether matching is case-sensitive (default: False)
        """
        self.score_boost = score_boost
        self.exact_match_boost = exact_match_boost
        self.case_sensitive = case_sensitive

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int | None = None,
    ) -> list[SearchResult]:
        """Rerank results based on similarity.

        Args:
            query: Search query
            results: Initial results
            top_k: Number of results to return

        Returns:
            Reranked results
        """
        if not results:
            return []

        # Prepare query
        query_text = query if self.case_sensitive else query.lower()
        query_terms = set(query_text.split())

        # Calculate new scores
        reranked = []
        for result in results:
            doc_text = result.document.text
            if not self.case_sensitive:
                doc_text = doc_text.lower()

            # Start with original score
            new_score = result.score

            # Boost for term matches
            doc_terms = set(doc_text.split())
            matching_terms = query_terms & doc_terms
            new_score += len(matching_terms) * self.score_boost

            # Boost for exact query match
            if query_text in doc_text:
                new_score += self.exact_match_boost

            reranked.append(
                SearchResult(
                    document=result.document,
                    score=new_score,
                    rank=0,  # Will be updated after sorting
                ),
            )

        # Sort by new score
        reranked.sort(key=lambda r: r.score, reverse=True)

        # Update ranks
        for rank, result in enumerate(reranked):
            reranked[rank] = replace(result, rank=rank)

        # Return top k
        if top_k is not None:
            return reranked[:top_k]
        return reranked


class DiversityReranker:
    """Diversity-based reranking.

    Reranks results to maximize diversity while maintaining relevance.
    Uses Maximal Marginal Relevance (MMR) approach.

    Example:
        >>> reranker = DiversityReranker(lambda_param=0.7)
        >>> results = await reranker.rerank("python", search_results)
    """

    def __init__(self, lambda_param: float = 0.7, similarity_threshold: float = 0.8):
        """Initialize diversity reranker.

        Args:
            lambda_param: Trade-off between relevance and diversity (0-1)
                         1.0 = pure relevance, 0.0 = pure diversity
            similarity_threshold: Similarity threshold for considering docs similar
        """
        self.lambda_param = lambda_param
        self.similarity_threshold = similarity_threshold

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int | None = None,
    ) -> list[SearchResult]:
        """Rerank results using MMR for diversity.

        Args:
            query: Search query
            results: Initial results
            top_k: Number of results to return

        Returns:
            Diverse reranked results
        """
        if not results:
            return []

        k = top_k or len(results)
        selected: list[SearchResult] = []
        remaining = results.copy()

        # Select first result (highest relevance)
        if remaining:
            first = max(remaining, key=lambda r: r.score)
            selected.append(first)
            remaining.remove(first)

        # Greedily select remaining results
        while len(selected) < k and remaining:
            best_score = float("-inf")
            best_result = None

            for result in remaining:
                # Relevance score
                relevance = result.score

                # Diversity score (inverse of max similarity to selected)
                max_sim = 0.0
                for selected_result in selected:
                    sim = self._calculate_similarity(
                        result.document.text,
                        selected_result.document.text,
                    )
                    max_sim = max(max_sim, sim)

                diversity = 1.0 - max_sim

                # MMR score
                mmr_score = (
                    self.lambda_param * relevance + (1 - self.lambda_param) * diversity
                )

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_result = result

            if best_result:
                selected.append(best_result)
                remaining.remove(best_result)

        # Update ranks
        for rank, result in enumerate(selected):
            selected[rank] = replace(result, rank=rank)

        return selected

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple Jaccard similarity between texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0-1)
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union)


class CustomReranker:
    """Custom reranking with user-defined scoring function.

    Example:
        >>> def my_scorer(query: str, doc: Document) -> float:
        ...     return len(doc.text)  # Prefer longer documents
        >>>
        >>> reranker = CustomReranker(score_fn=my_scorer)
        >>> results = await reranker.rerank("python", search_results)
    """

    def __init__(
        self,
        score_fn: Callable[[str, Document], float],
        combine_scores: bool = True,
        weight: float = 0.5,
    ):
        """Initialize custom reranker.

        Args:
            score_fn: Custom scoring function (query, document) -> score
            combine_scores: Whether to combine with original scores
            weight: Weight for custom score when combining (0-1)
        """
        self.score_fn = score_fn
        self.combine_scores = combine_scores
        self.weight = weight

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int | None = None,
    ) -> list[SearchResult]:
        """Rerank using custom scoring function.

        Args:
            query: Search query
            results: Initial results
            top_k: Number of results to return

        Returns:
            Reranked results
        """
        if not results:
            return []

        reranked = []
        for result in results:
            custom_score = self.score_fn(query, result.document)

            if self.combine_scores:
                # Combine original and custom scores
                final_score = (
                    self.weight * custom_score + (1 - self.weight) * result.score
                )
            else:
                final_score = custom_score

            reranked.append(
                SearchResult(
                    document=result.document,
                    score=final_score,
                    rank=0,
                ),
            )

        # Sort and update ranks
        reranked.sort(key=lambda r: r.score, reverse=True)
        for rank, result in enumerate(reranked):
            reranked[rank] = replace(result, rank=rank)

        if top_k is not None:
            return reranked[:top_k]
        return reranked


class CrossEncoderReranker:
    """Cross-encoder pattern for reranking.

    This class provides the structure and interface for cross-encoder reranking
    but doesn't include actual model loading (reserved for enterprise).

    In the community edition, this serves as a protocol/pattern that can be
    extended with actual models in the enterprise edition.

    Example:
        >>> # Community: Pattern only, no model
        >>> reranker = CrossEncoderReranker()
        >>> # Would need model in enterprise:
        >>> # reranker = CrossEncoderReranker(model="cross-encoder/ms-marco-MiniLM-L-6-v2")
    """

    def __init__(self, model: str | None = None, batch_size: int = 32):
        """Initialize cross-encoder reranker.

        Args:
            model: Model name/path (enterprise only)
            batch_size: Batch size for inference
        """
        self.model = model
        self.batch_size = batch_size
        self._model_loaded = False

        if model is not None:
            raise NotImplementedError(
                "Cross-encoder model loading is not supported in the current version.",
            )

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int | None = None,
    ) -> list[SearchResult]:
        """Rerank using cross-encoder model.

        Args:
            query: Search query
            results: Initial results
            top_k: Number of results to return

        Returns:
            Reranked results

        Raises:
            NotImplementedError: If not implemented
        """
        raise NotImplementedError(
            "Cross-encoder inference is not supported in the current version.",
        )


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
    msg = f"Unknown reranking strategy: {strategy}"
    raise ValueError(msg)


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
