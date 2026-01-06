from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from lexigram.contracts.data.vector.types import SearchResult


@runtime_checkable
class Reranker(Protocol):
    """Reranks search results by relevance, diversity, or custom scoring."""

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int | None = None,
    ) -> list[SearchResult]: ...


@runtime_checkable
class VectorRetriever(Protocol):
    """Retrieves documents via vector similarity search."""

    async def search(
        self,
        query: str,
        k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[SearchResult]: ...


@runtime_checkable
class Tokenizer(Protocol):
    """Tokenizes text for BM25 scoring."""

    def tokenize(self, text: str) -> list[str]: ...


__all__ = ["Reranker", "Tokenizer", "VectorRetriever"]
