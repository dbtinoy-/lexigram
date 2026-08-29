"""Chunking strategy registry for RAG document splitting.

Maps :class:`~lexigram.ai.rag.chunking.types.ChunkingStrategy` enum values
to chunker *classes* and instantiates on demand.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.rag.chunking.types import ChunkingConfig, ChunkingStrategy
from lexigram.logging import (
    get_logger,
)
from lexigram.primitives.registry import StrategyRegistry

if TYPE_CHECKING:
    from lexigram.ai.rag.chunking.base import AbstractChunker

logger = get_logger(__name__)


class ChunkingStrategyRegistry(StrategyRegistry):
    """Registry mapping chunking strategy names to chunker classes.

    Usage::

        registry = ChunkingStrategyRegistry.with_defaults()
        chunker = registry.instantiate(
            ChunkingStrategy.FIXED_SIZE, chunk_size=512, overlap=100,
        )
    """

    def __init__(self) -> None:
        super().__init__(name="chunking.strategies", allow_overwrite=True)

    def create_chunker(
        self,
        strategy: ChunkingStrategy = ChunkingStrategy.FIXED_SIZE,
        config: ChunkingConfig | None = None,
        **kwargs: Any,
    ) -> AbstractChunker:
        """Create a chunker instance for the given strategy.

        Merges *config* defaults with explicit *kwargs* (kwargs win).

        Args:
            strategy: Which chunking strategy to use.
            config: Optional chunking config; fields used as defaults.
            **kwargs: Constructor overrides forwarded to the chunker class.

        Returns:
            A configured :class:`Chunker` instance.
        """
        config = config or ChunkingConfig()
        merged = self._merge_config(strategy, config, kwargs)
        return self.instantiate(strategy, **merged)

    @staticmethod
    def _merge_config(
        strategy: ChunkingStrategy,
        config: ChunkingConfig,
        overrides: dict[str, Any],
    ) -> dict[str, Any]:
        """Build kwargs from config with overrides applied."""
        base: dict[str, Any] = {}
        if strategy == ChunkingStrategy.FIXED_SIZE:
            base = {
                "chunk_size": overrides.get("chunk_size", config.chunk_size),
                "overlap": overrides.get("overlap", config.overlap),
            }
        elif strategy == ChunkingStrategy.RECURSIVE:
            base = {
                "chunk_size": overrides.get("chunk_size", config.chunk_size),
                "overlap": overrides.get("overlap", config.overlap),
                "separators": overrides.get("separators", config.separators),
            }
        elif strategy == ChunkingStrategy.SEMANTIC:
            base = {
                "max_chunk_size": overrides.get("chunk_size", config.chunk_size),
                "min_chunk_size": overrides.get(
                    "min_chunk_size", config.min_chunk_size
                ),
            }
        elif strategy == ChunkingStrategy.SLIDING_WINDOW:
            stride = overrides.get("stride")
            if stride is None:
                overlap = overrides.get("overlap", config.overlap)
                chunk_size = overrides.get("chunk_size", config.chunk_size)
                stride = max(1, chunk_size - overlap)
            base = {
                "window_size": overrides.get("chunk_size", config.chunk_size),
                "stride": stride,
            }
        elif strategy == ChunkingStrategy.TOKEN:
            base = {
                "chunk_size": overrides.get("chunk_size", config.chunk_size),
                "overlap": overrides.get("overlap", config.overlap),
                "encoding_name": overrides.get("encoding_name", config.encoding_name),
            }
        return base

    @classmethod
    def default_strategies(cls) -> dict[str, type]:
        """Return built-in strategy key → class mapping."""
        from lexigram.ai.rag.chunking.strategies.fixed_size import FixedSizeChunker
        from lexigram.ai.rag.chunking.strategies.recursive import RecursiveChunker
        from lexigram.ai.rag.chunking.strategies.semantic import SemanticChunker
        from lexigram.ai.rag.chunking.strategies.sliding_window import (
            SlidingWindowChunker,
        )
        from lexigram.ai.rag.chunking.strategies.token import TokenChunker

        return {
            ChunkingStrategy.FIXED_SIZE: FixedSizeChunker,
            ChunkingStrategy.RECURSIVE: RecursiveChunker,
            ChunkingStrategy.SEMANTIC: SemanticChunker,
            ChunkingStrategy.SLIDING_WINDOW: SlidingWindowChunker,
            ChunkingStrategy.TOKEN: TokenChunker,
        }
