"""Deterministic local embeddings for the RAG demo.

Storage is deliberately not implemented here.  The application composes
Lexigram's ``VectorModule`` and ``VectorStoreProtocol``; this tiny embedder
only makes the demo runnable without an external embedding API.
"""

from __future__ import annotations

import hashlib
import math


class DeterministicEmbedder:
    """Create repeatable vectors without network or model dependencies.

    The interface mirrors the small part of an embedding client used by the
    retriever.  Swap this class for a hosted embedding client in a real app;
    the Lexigram vector collection does not change.
    """

    def __init__(self, dimension: int = 128) -> None:
        if dimension < 1:
            raise ValueError("embedding dimension must be positive")
        self.dimension = dimension

    def embed(self, text: str) -> list[float]:
        """Return a normalized, deterministic vector for ``text``."""
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = [
            (digest[index % len(digest)] / 255.0) * 2.0 - 1.0
            for index in range(self.dimension)
        ]
        norm = math.sqrt(sum(value * value for value in values))
        return [value / norm for value in values] if norm else values


__all__ = ["DeterministicEmbedder"]
