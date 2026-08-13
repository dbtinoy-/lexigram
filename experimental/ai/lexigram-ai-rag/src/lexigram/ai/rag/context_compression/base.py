"""Base compressor class for context compression."""

from __future__ import annotations

from abc import ABC, abstractmethod

from lexigram.ai.rag.context_compression.types import CompressionResult

"""Convenience function for context compression."""

from typing import Any

from lexigram.ai.rag.context_compression.types import (
    CompressionStrategy,
)


async def compress_context(
    context: str | list[str],
    strategy: CompressionStrategy = CompressionStrategy.EXTRACTIVE,
    query: str | None = None,
    **kwargs: Any,
) -> CompressionResult:
    """Convenience function for context compression.

    Args:
        context: Text or list of texts to compress.
        strategy: Compression strategy to use.
        query: Optional query for relevance-based compression.
        **kwargs: Strategy-specific parameters.

    Returns:
        CompressionResult.

    Example:
        >>> result = await compress_context(
        ...     context=long_text,
        ...     strategy=CompressionStrategy.EXTRACTIVE,
        ...     query="What is AI?",
        ...     max_sentences=5
        ... )
    """
    from lexigram.ai.rag.context_compression.strategy_registry import (
        CompressionStrategyRegistry,
    )

    registry = CompressionStrategyRegistry.with_defaults()
    return await registry.compress(strategy, context, query, kwargs)


class AbstractCompressor(ABC):
    """Base class for context compressors."""

    @abstractmethod
    async def compress(
        self,
        context: str | list[str],
        query: str | None = None,
        **kwargs,
    ) -> CompressionResult:
        """Compress context.

        Args:
            context: Text or list of texts to compress.
            query: Optional query for relevance-based compression.
            **kwargs: Additional compression parameters.

        Returns:
            CompressionResult with compressed text and statistics.
        """

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation).

        Uses simple heuristic: ~4 characters per token on average.
        For production, use tiktoken or similar.
        """
        return len(text) // 4

    def _normalize_context(self, context: str | list[str]) -> str:
        """Normalize context to single string."""
        if isinstance(context, list):
            return "\n\n".join(str(c) for c in context)
        return str(context)
