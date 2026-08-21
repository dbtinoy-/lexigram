"""Deterministic stdlib-only hashing embedder (no network, no model)."""

from __future__ import annotations

import hashlib
import re

from lexigram.contracts.ai.llm import EmbeddingClientProtocol

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class HashingEmbedder(EmbeddingClientProtocol):
    """BLAKE2b token-hashing embedder, deterministic across processes.

    Args:
        dimension: Embedding dimensionality (bucket count).
    """

    def __init__(self, dimension: int = 256) -> None:
        self._dimension = dimension

    def _embed_one(self, text: str) -> list[float]:
        buckets = [0.0] * self._dimension
        for token in _TOKEN_RE.findall(text.lower()):
            digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
            index = int.from_bytes(digest, "big") % self._dimension
            weight = float(digest[0]) + 1.0
            buckets[index] += weight
        norm = sum(component * component for component in buckets) ** 0.5
        if norm == 0.0:
            return buckets
        return [component / norm for component in buckets]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts into fixed-dimension unit vectors.

        Args:
            texts: Texts to embed.

        Returns:
            One L2-normalized vector per input text.
        """
        return [self._embed_one(text) for text in texts]


__all__ = ["HashingEmbedder"]
