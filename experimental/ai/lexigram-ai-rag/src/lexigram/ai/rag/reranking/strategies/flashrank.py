"""FlashRank reranking strategy using flashrank library."""

from __future__ import annotations

import asyncio
import importlib.util
from typing import Any

from lexigram.ai.rag.reranking.types import RerankResult
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


def _flashrank_available() -> bool:
    """Check if flashrank package is installed."""
    try:
        return importlib.util.find_spec("flashrank") is not None
    except (ValueError, AttributeError):
        return False


class FlashRankRerankerStrategy:
    """FlashRank document reranking strategy using cross-encoders.

    Reranks documents using the flashrank library with minimal dependencies
    and high speed. Suitable for production use with pre-cached rankings.

    Raises ImportError at instantiation if flashrank is not installed.
    """

    def __init__(
        self,
        model_name: str = "ms-marco-MiniLM-L-12-v2",
        max_length: int = 512,
    ) -> None:
        """Initialize the FlashRank reranker.

        Args:
            model_name: Model name for flashrank. Defaults to ms-marco-MiniLM-L-12-v2.
            max_length: Maximum sequence length for the model.

        Raises:
            ImportError: If flashrank package is not installed.
        """
        from flashrank import Ranker  # type: ignore[import-not-found]

        self._model_name = model_name
        self._max_length = max_length
        # Let flashrank handle cache directory via its defaults
        self._ranker = Ranker(model_name=model_name)

    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int | None = None,
        **kwargs: Any,
    ) -> RerankResult:
        """Rerank documents by relevance to the query using FlashRank.

        Wraps the synchronous flashrank.Ranker call in an executor to avoid
        blocking the event loop.

        Args:
            query: The query string.
            documents: List of documents to rerank.
            top_k: Return only top k documents. None = return all.
            **kwargs: Additional arguments (unused).

        Returns:
            RerankResult with reranked documents and relevance scores.
        """
        from flashrank import RerankRequest

        # Prepare passages for flashrank
        passages = [{"id": i, "text": doc} for i, doc in enumerate(documents)]
        request = RerankRequest(query=query, passages=passages)

        # Run synchronous ranker in thread pool
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: self._ranker.rerank(request),
        )

        # Sort by score descending (already sorted by flashrank, but explicit)
        sorted_results = sorted(results, key=lambda x: x["score"], reverse=True)

        # Apply top_k filter if provided
        if top_k is not None:
            sorted_results = sorted_results[:top_k]

        reranked_docs = [r["text"] for r in sorted_results]
        scores = [r["score"] for r in sorted_results]

        return RerankResult(
            documents=reranked_docs,
            scores=scores,
            original_count=len(documents),
            reranked_count=len(reranked_docs),
            model_name=self._model_name,
        )


class FlashRankStrategyHandler:
    """Handler adapter for FlashRankRerankerStrategy.

    Provides the can_handle() and create_and_rerank() interface expected
    by RerankingStrategyRegistry. Uses lazy loading with config-based caching
    to avoid loading the model multiple times.
    """

    def __init__(self) -> None:
        """Initialize the handler with no strategy yet (lazy loading)."""
        self._strategy: FlashRankRerankerStrategy | None = None
        self._model_name: str = "ms-marco-MiniLM-L-12-v2"
        self._max_length: int = 512

    def can_handle(self, strategy: Any) -> bool:
        """Check if this handler can handle the given strategy name.

        Args:
            strategy: Strategy name to check.

        Returns:
            True if strategy == "flashrank", False otherwise.
        """
        return strategy == "flashrank"

    def _get_or_create_strategy(
        self, model_name: str, max_length: int
    ) -> FlashRankRerankerStrategy:
        """Return cached strategy if config matches, else create and cache new one.

        Args:
            model_name: Model name for flashrank.
            max_length: Maximum sequence length for the model.

        Returns:
            FlashRankRerankerStrategy instance, cached for this config.
        """
        if (
            self._strategy is None
            or self._model_name != model_name
            or self._max_length != max_length
        ):
            self._strategy = FlashRankRerankerStrategy(
                model_name=model_name,
                max_length=max_length,
            )
            self._model_name = model_name
            self._max_length = max_length
        return self._strategy

    async def create_and_rerank(
        self,
        strategy: str,
        query: str,
        documents: list[str],
        **kwargs: Any,
    ) -> RerankResult:
        """Rerank documents using FlashRank, reusing cached strategy if config unchanged.

        Args:
            strategy: Strategy name (ignored, always "flashrank").
            query: The query string.
            documents: List of documents to rerank.
            **kwargs: Arguments passed to FlashRankRerankerStrategy and rerank.
                Supports model_name, max_length, top_k, etc.

        Returns:
            RerankResult from the underlying strategy.
        """
        model_name = kwargs.pop("model_name", "ms-marco-MiniLM-L-12-v2")
        max_length = kwargs.pop("max_length", 512)
        reranker = self._get_or_create_strategy(model_name, max_length)
        return await reranker.rerank(query=query, documents=documents, **kwargs)


__all__ = ["FlashRankRerankerStrategy", "FlashRankStrategyHandler"]
