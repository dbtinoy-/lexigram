"""OpenAI-compatible embedding client for lexigram-vector."""

from __future__ import annotations

from lexigram.vector.embedding.cache import EmbeddingCache, InMemoryEmbeddingCache
from lexigram.vector.embedding.client import OpenAICompatibleEmbeddingClient
from lexigram.vector.embedding.config import EmbeddingClientConfig

__all__ = [
    "EmbeddingCache",
    "EmbeddingClientConfig",
    "InMemoryEmbeddingCache",
    "OpenAICompatibleEmbeddingClient",
]
