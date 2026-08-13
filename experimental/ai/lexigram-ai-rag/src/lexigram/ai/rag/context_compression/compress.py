"""Convenience function for context compression."""

from __future__ import annotations

from typing import Any

from lexigram.ai.rag.context_compression.strategy_registry import (
    CompressionStrategyRegistry,
)
from lexigram.ai.rag.context_compression.types import (
    CompressionResult,
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
    registry = CompressionStrategyRegistry.with_defaults()
    return await registry.compress(strategy, context, query, kwargs)
