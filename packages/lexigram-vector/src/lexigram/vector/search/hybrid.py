"""Hybrid search combining BM25 and vector similarity.

This module provides hybrid retrieval that combines keyword-based BM25 search
with semantic vector search using Reciprocal Rank Fusion (RRF).

Example:
    >>> from lexigram.contracts.ai.vector import Document
    >>> from lexigram.vector.search.hybrid import HybridRetriever
    >>>
    >>> # Create retriever
    >>> retriever = HybridRetriever(vector_store=my_vector_store)
    >>>
    >>> # Add documents
    >>> await retriever.add_documents([
    ...     Document(text="Python is a programming language"),
    ...     Document(text="Java is also a programming language")
    ... ])
    >>>
    >>> # Hybrid search
    >>> results = await retriever.search("python programming", k=5)
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Protocol

from lexigram.contracts.ai.vector import Document, RAGSearchResult
from lexigram.domain.models.base import DomainModel
from lexigram.validation import Field
from lexigram.vector.search.bm25 import (  # noqa: F401 — re-exported for backwards compat
    BM25Retriever,
    BM25Scorer,
    SimpleTokenizer,
    Tokenizer,
)

SearchResult = RAGSearchResult

__all__ = [
    "BM25Retriever",
    "BM25Scorer",
    "HybridRetriever",
    "HybridSearchConfig",
    "RRFReranker",
    "SimpleTokenizer",
    "Tokenizer",
    "VectorRetriever",
    "create_hybrid_retriever",
]


class VectorRetriever(Protocol):
    """Protocol for vector-based retrieval."""

    async def search(
        self,
        query: str,
        k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Search for documents using vector similarity.

        Args:
            query: Search query
            k: Number of results to return
            filter: Optional metadata filter

        Returns:
            List of search results
        """
        ...


class RRFReranker:
    """Reciprocal Rank Fusion (RRF) for combining ranked lists.

    RRF is a simple and effective method for combining multiple ranked lists.
    It gives higher scores to items that appear near the top of multiple lists.

    Example:
        >>> reranker = RRFReranker(k=60)
        >>> fused = reranker.fuse([results1, results2])
    """

    def __init__(self, k: int = 60):
        """Initialize RRF reranker.

        Args:
            k: RRF constant parameter (default: 60)
        """
        self.k = k

    def fuse(
        self,
        ranked_lists: list[list[SearchResult]],
        weights: list[float] | None = None,
    ) -> list[SearchResult]:
        """Fuse multiple ranked lists using RRF.

        Args:
            ranked_lists: List of ranked result lists
            weights: Optional weights for each list (default: equal weights)

        Returns:
            Fused and re-ranked results
        """
        if not ranked_lists:
            return []

        # Default to equal weights
        if weights is None:
            weights = [1.0] * len(ranked_lists)
        elif len(weights) != len(ranked_lists):
            msg = "weights length must match number of ranked lists"
            raise ValueError(msg)

        # Calculate RRF scores
        rrf_scores: dict[str, float] = defaultdict(float)
        doc_map: dict[str, Document] = {}

        for rank_list, weight in zip(ranked_lists, weights, strict=False):
            for result in rank_list:
                doc_id = result.document.id or result.document.text[:50]
                doc_map[doc_id] = result.document

                # RRF formula: weight / (k + rank)
                rrf_scores[doc_id] += weight / (self.k + result.rank)

        # Sort by RRF score descending
        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        # Create results
        results = []
        for rank, (doc_id, score) in enumerate(sorted_docs):
            results.append(
                SearchResult(
                    document=doc_map[doc_id],
                    score=score,
                    rank=rank,
                ),
            )

        return results


class HybridRetriever:
    """Hybrid retrieval combining BM25 and vector search.

    Uses Reciprocal Rank Fusion (RRF) to combine results from both methods.

    Example:
        >>> retriever = HybridRetriever(
        ...     vector_store=my_vector_store,
        ...     bm25_weight=0.5,
        ...     vector_weight=0.5
        ... )
        >>> results = await retriever.search("python programming", k=10)
    """

    def __init__(
        self,
        vector_store: VectorRetriever,
        bm25_weight: float = 0.5,
        vector_weight: float = 0.5,
        rrf_k: int = 60,
        tokenizer: Tokenizer | None = None,
    ):
        """Initialize hybrid retriever.

        Args:
            vector_store: Vector store for semantic search
            bm25_weight: Weight for BM25 results (default: 0.5)
            vector_weight: Weight for vector results (default: 0.5)
            rrf_k: RRF k parameter (default: 60)
            tokenizer: Text tokenizer for BM25
        """
        self.vector_store = vector_store
        self.bm25_retriever = BM25Retriever(tokenizer=tokenizer)
        self.reranker = RRFReranker(k=rrf_k)
        self.bm25_weight = bm25_weight
        self.vector_weight = vector_weight

    async def add_documents(self, documents: list[Document]) -> None:
        """Add documents to both BM25 and vector stores.

        Args:
            documents: Documents to add
        """
        # Add to BM25 index
        self.bm25_retriever.add_documents(documents)

        # Note: Vector store addition should be handled separately
        # as it typically requires async operations and embeddings

    async def search(
        self,
        query: str,
        k: int = 10,
        bm25_k: int | None = None,
        vector_k: int | None = None,
        filter: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Perform hybrid search.

        Args:
            query: Search query
            k: Number of final results to return
            bm25_k: Number of BM25 results (default: k * 2)
            vector_k: Number of vector results (default: k * 2)
            filter: Optional metadata filter for vector search

        Returns:
            Fused and re-ranked search results
        """
        # Retrieve more results from each method than needed
        # This gives RRF more data to work with
        bm25_k = bm25_k or k * 2
        vector_k = vector_k or k * 2

        # Get BM25 results (synchronous)
        bm25_results = self.bm25_retriever.search(query, k=bm25_k)

        # Get vector results (async)
        vector_results = await self.vector_store.search(
            query,
            k=vector_k,
            filter=filter,
        )

        # Fuse results using RRF
        fused_results = self.reranker.fuse(
            [bm25_results, vector_results],
            weights=[self.bm25_weight, self.vector_weight],
        )

        # Return top k
        return fused_results[:k]

    def clear(self) -> None:
        """Clear BM25 index.

        Note: Vector store should be cleared separately.
        """
        self.bm25_retriever.clear()


@dataclass(init=False)
class HybridSearchConfig(DomainModel):
    """Configuration for hybrid search.

    Example:
        >>> config = HybridSearchConfig(
        ...     bm25_weight=0.6,
        ...     vector_weight=0.4,
        ...     rrf_k=60
        ... )
    """

    bm25_weight: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Weight for BM25 results",
    )
    vector_weight: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Weight for vector results",
    )
    rrf_k: int = Field(
        default=60,
        ge=1,
        description="RRF k parameter",
    )
    bm25_k1: float = Field(
        default=1.5,
        ge=0.0,
        description="BM25 k1 parameter",
    )
    bm25_b: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="BM25 b parameter",
    )


def create_hybrid_retriever(
    vector_store: VectorRetriever,
    config: HybridSearchConfig | None = None,
) -> HybridRetriever:
    """Create a hybrid retriever with configuration.

    Args:
        vector_store: Vector store for semantic search
        config: Hybrid search configuration

    Returns:
        Configured hybrid retriever

    Example:
        >>> config = HybridSearchConfig(bm25_weight=0.6, vector_weight=0.4)
        >>> retriever = create_hybrid_retriever(my_vector_store, config)
    """
    config = config or HybridSearchConfig()

    return HybridRetriever(
        vector_store=vector_store,
        bm25_weight=config.bm25_weight,
        vector_weight=config.vector_weight,
        rrf_k=config.rrf_k,
        tokenizer=SimpleTokenizer(),
    )
