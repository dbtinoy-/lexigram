"""
Protocol definitions for batch embedding components.
"""

from __future__ import annotations

from typing import Protocol


class EmbeddingProvider(Protocol):
    """Protocol for embedding providers."""

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts."""
        ...
