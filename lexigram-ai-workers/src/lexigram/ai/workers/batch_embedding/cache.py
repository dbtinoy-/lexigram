"""
Embedding cache management for batch embedding operations.
"""

from __future__ import annotations

import asyncio

from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class EmbeddingCache:
    """
    Simple in-memory cache for embeddings.

    Enterprise version would use distributed cache (Redis).
    """

    def __init__(self) -> None:
        """Initialize embedding cache."""
        self._cache: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    async def get(self, text: str, model_name: str) -> list[float] | None:
        """Get cached embedding for text."""
        cache_key = f"{model_name}:{hash(text)}"
        async with self._lock:
            return self._cache.get(cache_key)

    async def set(self, text: str, model_name: str, embedding: list[float]) -> None:
        """Cache embedding for text."""
        cache_key = f"{model_name}:{hash(text)}"
        async with self._lock:
            self._cache[cache_key] = embedding

    async def get_batch(
        self,
        texts: list[str],
        model_name: str,
    ) -> tuple[list[list[float] | None], list[tuple[int, str]]]:
        """
        Get cached embeddings for batch of texts.

        Returns:
            (cached_embeddings, uncached_indices_and_texts)
        """
        cached_embeddings: list[list[float] | None] = []
        uncached: list[tuple[int, str]] = []

        async with self._lock:
            for i, text in enumerate(texts):
                cache_key = f"{model_name}:{hash(text)}"
                embedding = self._cache.get(cache_key)
                if embedding is not None:
                    cached_embeddings.append(embedding)
                else:
                    cached_embeddings.append(None)
                    uncached.append((i, text))

        return cached_embeddings, uncached

    async def set_batch(
        self,
        texts_and_embeddings: list[tuple[str, list[float]]],
        model_name: str,
    ) -> None:
        """Cache multiple embeddings."""
        async with self._lock:
            for text, embedding in texts_and_embeddings:
                cache_key = f"{model_name}:{hash(text)}"
                self._cache[cache_key] = embedding

    async def clear(self) -> None:
        """Clear all cached embeddings."""
        async with self._lock:
            self._cache.clear()
        logger.info("Cleared embedding cache")

    def size(self) -> int:
        """Get number of cached embeddings."""
        return len(self._cache)

    async def get_embeddings_with_cache(
        self,
        texts: list[str],
        model_name: str,
        embedding_provider: EmbeddingProvider,  # type: ignore[name-defined]
    ) -> tuple[list[list[float]], int, int]:
        """
        Get embeddings with cache lookup and generation.

        Returns:
            (embeddings, cache_hits, cache_misses)
        """
        embeddings: list[list[float]] = []
        cache_hits = 0
        cache_misses = 0

        # Check cache first
        cached_embeddings, _uncached_texts = await self.get_batch(texts, model_name)

        # Fill in cached results and collect uncached texts
        uncached_indices_and_texts: list[tuple[int, str]] = []
        for i, (text, cached) in enumerate(zip(texts, cached_embeddings, strict=False)):
            if cached is not None:
                embeddings.append(cached)
                cache_hits += 1
            else:
                embeddings.append([])  # Placeholder
                uncached_indices_and_texts.append((i, text))
                cache_misses += 1

        # Generate embeddings for cache misses
        if uncached_indices_and_texts:
            uncached_only = [x[1] for x in uncached_indices_and_texts]

            new_embeddings = await embedding_provider.embed_texts(uncached_only)

            # Cache new embeddings and update results
            await self.set_batch(
                list(zip(uncached_only, new_embeddings, strict=False)),
                model_name,
            )

            for (idx, _), embedding in zip(
                uncached_indices_and_texts,
                new_embeddings,
                strict=False,
            ):
                embeddings[idx] = embedding

        return embeddings, cache_hits, cache_misses
