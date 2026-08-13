"""Types for reranking operations."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RerankResult:
    """Result of a reranking operation.

    Attributes:
        documents: Reranked documents (most relevant first).
        scores: Relevance scores (parallel to documents).
        original_count: Number of documents passed to reranker.
        reranked_count: Number of documents returned (may be < original if top_k applied).
        model_name: Name of the reranking model used.
        metadata: Additional reranking metadata.
    """

    documents: list[str]
    scores: list[float]
    original_count: int
    reranked_count: int
    model_name: str
    metadata: dict = field(default_factory=dict)
