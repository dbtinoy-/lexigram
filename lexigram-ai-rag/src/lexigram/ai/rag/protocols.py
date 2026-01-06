from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ChunkerProtocol(Protocol):
    """Splits documents into chunks for embedding and indexing."""

    def chunk(self, text: str, chunk_size: int, overlap: int) -> list[str]: ...


@runtime_checkable
class RerankerProtocol(Protocol):
    """Re-ranks retrieved documents by relevance."""

    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int,
    ) -> list[tuple[str, float]]: ...


@runtime_checkable
class ContextCompressorProtocol(Protocol):
    """Compresses retrieved context to fit within token limits."""

    async def compress(self, query: str, context: str, max_tokens: int) -> str: ...
