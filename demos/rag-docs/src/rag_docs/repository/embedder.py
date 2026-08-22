"""Deterministic stdlib-only hashing embedder (no network, no model)."""

from __future__ import annotations

import hashlib
import math
import re

from lexigram.contracts.ai.llm import EmbeddingClientProtocol

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_EMBEDDING_DIMENSION = 1024
_STOP_DF_RATIO = 0.30
_DEFAULT_IDF_WEIGHT = 1.0


def _stem(token: str) -> str:
    """Strip light English suffixes so inflections share one bucket."""
    for suffix in ("ing", "ed", "es", "s"):
        if len(token) > 4 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def _tokenize(text: str) -> set[str]:
    """Lowercase, tokenize, and stem; unique tokens vote once."""
    return {_stem(token) for token in _TOKEN_RE.findall(text.lower())}


class HashingEmbedder(EmbeddingClientProtocol):
    """Signed BLAKE2b feature-hashing embedder with corpus-fitted IDF.

    Deterministic across processes. Unique stemmed tokens hash into
    ``dimension`` buckets with a ±1 sign (colliding tokens cancel instead
    of accumulating). After :meth:`fit`, votes are scaled by smoothed
    inverse document frequency and corpus-frequent tokens (df ratio above
    ``_STOP_DF_RATIO``) are zeroed, so rare distinctive terms dominate.
    Unfitted instances weight every token equally.

    Args:
        dimension: Embedding dimensionality (bucket count).
    """

    def __init__(self, dimension: int = _EMBEDDING_DIMENSION) -> None:
        self._dimension = dimension
        self._idf: dict[str, float] = {}
        self._stop: set[str] = set()
        self._unseen_weight = _DEFAULT_IDF_WEIGHT
        self._fitted = False

    def fit(self, texts: list[str]) -> None:
        """Compute corpus statistics (IDF weights, stopwords).

        Deterministic: identical texts yield identical statistics.

        Args:
            texts: Every document/chunk text in the corpus.
        """
        document_frequency: dict[str, int] = {}
        for text in texts:
            for token in _tokenize(text):
                document_frequency[token] = document_frequency.get(token, 0) + 1
        total = len(texts)
        # The df-ratio stop rule needs a real corpus; tiny ones would zero
        # nearly every token (a 2-chunk corpus gives any token ratio 0.5).
        if total < 20:
            self._stop = set()
        else:
            self._stop = {
                token
                for token, count in document_frequency.items()
                if count / total > _STOP_DF_RATIO
            }
        self._idf = {
            token: math.log((total + 1) / (count + 1)) + 1.0
            for token, count in document_frequency.items()
        }
        self._unseen_weight = math.log(total + 2) if total else _DEFAULT_IDF_WEIGHT
        self._fitted = True

    def _embed_one(self, text: str) -> list[float]:
        """Bucket unique stemmed tokens (signed, IDF-weighted), L2-normalize."""
        buckets = [0.0] * self._dimension
        for token in _tokenize(text):
            if self._fitted and token in self._stop:
                continue
            digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
            sign = 1.0 if digest[0] < 128 else -1.0
            index = int.from_bytes(digest[1:], "big") % self._dimension
            weight = (
                self._idf.get(token, self._unseen_weight)
                if self._fitted
                else _DEFAULT_IDF_WEIGHT
            )
            buckets[index] += sign * weight
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


EMBEDDING_DIMENSION = _EMBEDDING_DIMENSION

__all__ = ["EMBEDDING_DIMENSION", "HashingEmbedder"]
