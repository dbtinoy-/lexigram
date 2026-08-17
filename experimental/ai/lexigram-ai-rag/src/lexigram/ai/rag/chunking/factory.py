"""Factory functions for creating chunkers.

.. warning::
   This module is designed to work as a standalone library.
   It should NOT import from any Lexigram framework modules.

The :func:`create_chunker` function delegates to
:class:`~lexigram.ai.rag.chunking.strategy_registry.ChunkingStrategyRegistry`
for extensible strategy dispatch.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.rag.chunking.types import ChunkingConfig, ChunkingStrategy

if TYPE_CHECKING:
    from lexigram.ai.rag.chunking.base import AbstractChunker


def create_chunker(
    strategy: ChunkingStrategy = ChunkingStrategy.FIXED_SIZE,
    config: ChunkingConfig | None = None,
    **kwargs: Any,
) -> AbstractChunker:
    """Create a chunker instance for the given strategy.

    Convenience wrapper around :class:`ChunkingStrategyRegistry`.

    Args:
        strategy: Which chunking strategy to use.
        config: Optional chunking configuration.
        **kwargs: Additional keyword arguments forwarded to the chunker
            constructor (override config defaults).

    Returns:
        A configured :class:`Chunker` instance.

    Raises:
        ValueError: If no chunker is registered for the given *strategy*.
    """
    from lexigram.ai.rag.chunking.strategy_registry import ChunkingStrategyRegistry

    registry = ChunkingStrategyRegistry.with_defaults()
    return registry.create_chunker(strategy, config, **kwargs)
