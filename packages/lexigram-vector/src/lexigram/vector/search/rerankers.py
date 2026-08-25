"""Concrete reranker implementations for search result re-ordering.

This module houses the reranker family (similarity, diversity, custom,
cross-encoder).  Strategy selection lives in
:mod:`lexigram.vector.search.reranking` via :func:`create_reranker`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from lexigram.contracts.ai.vector import Document, RAGSearchResult

SearchResult = RAGSearchResult

__all__ = [
    "CrossEncoderReranker",
    "CustomReranker",
    "DiversityReranker",
    "SearchResult",
    "SimilarityReranker",
]


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
