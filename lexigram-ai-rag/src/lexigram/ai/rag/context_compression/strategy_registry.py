"""Compression strategy registry for RAG context compression."""

from __future__ import annotations

from typing import Any, Protocol

from lexigram.ai.rag.context_compression.abstractive import AbstractiveCompressor
from lexigram.ai.rag.context_compression.extractive import ExtractiveSummaryCompressor
from lexigram.ai.rag.context_compression.hybrid import HybridCompressor
from lexigram.ai.rag.context_compression.semantic_dedup import (
    SemanticDeduplicationCompressor,
)
from lexigram.ai.rag.context_compression.token_limit import TokenLimitCompressor
from lexigram.ai.rag.context_compression.types import CompressionStrategy


class CompressionStrategyHandler(Protocol):
    """Protocol for compression strategy handlers."""

    def can_handle(self, strategy: Any) -> bool:
        """Check if this handler can handle the strategy."""
        ...

    async def create_and_compress(
        self,
        strategy: Any,
        context: Any,
        query: Any,
        kwargs: dict[str, Any],
    ) -> Any:
        """Create compressor and compress context."""
        ...


class ExtractiveStrategyHandler:
    """Handler for extractive compression strategy."""

    def can_handle(self, strategy: Any) -> bool:
        return strategy == CompressionStrategy.EXTRACTIVE

    async def create_and_compress(
        self,
        strategy: Any,
        context: Any,
        query: Any,
        kwargs: dict[str, Any],
    ) -> Any:
        compressor = ExtractiveSummaryCompressor(**kwargs)
        return await compressor.compress(context, query=query)


class AbstractiveStrategyHandler:
    """Handler for abstractive compression strategy."""

    def can_handle(self, strategy: Any) -> bool:
        return strategy == CompressionStrategy.ABSTRACTIVE

    async def create_and_compress(
        self,
        strategy: Any,
        context: Any,
        query: Any,
        kwargs: dict[str, Any],
    ) -> Any:
        if "llm_client" not in kwargs:
            msg = "AbstractiveCompressor requires 'llm_client' parameter"
            raise ValueError(msg)
        compressor = AbstractiveCompressor(**kwargs)
        return await compressor.compress(context, query=query)


class TokenLimitStrategyHandler:
    """Handler for token limit compression strategy."""

    def can_handle(self, strategy: Any) -> bool:
        return strategy == CompressionStrategy.TOKEN_LIMIT

    async def create_and_compress(
        self,
        strategy: Any,
        context: Any,
        query: Any,
        kwargs: dict[str, Any],
    ) -> Any:
        compressor = TokenLimitCompressor(**kwargs)
        return await compressor.compress(context, query=query)


class SemanticDedupStrategyHandler:
    """Handler for semantic deduplication compression strategy."""

    def can_handle(self, strategy: Any) -> bool:
        return strategy == CompressionStrategy.SEMANTIC_DEDUP

    async def create_and_compress(
        self,
        strategy: Any,
        context: Any,
        query: Any,
        kwargs: dict[str, Any],
    ) -> Any:
        compressor = SemanticDeduplicationCompressor(**kwargs)
        return await compressor.compress(context, query=query)


class HybridStrategyHandler:
    """Handler for hybrid compression strategy."""

    def can_handle(self, strategy: Any) -> bool:
        return strategy == CompressionStrategy.HYBRID

    async def create_and_compress(
        self,
        strategy: Any,
        context: Any,
        query: Any,
        kwargs: dict[str, Any],
    ) -> Any:
        if "compressors" not in kwargs:
            msg = "HybridCompressor requires 'compressors' parameter"
            raise ValueError(msg)
        compressor = HybridCompressor(**kwargs)
        return await compressor.compress(context, query=query)


class CompressionStrategyRegistry:
    """Central registry for compression strategy handlers."""

    def __init__(self) -> None:
        self._handlers: list[CompressionStrategyHandler] = []

    @classmethod
    def with_defaults(cls) -> CompressionStrategyRegistry:
        """Create a registry pre-populated with all built-in strategy handlers."""
        registry = cls()
        registry._handlers = [
            ExtractiveStrategyHandler(),
            AbstractiveStrategyHandler(),
            TokenLimitStrategyHandler(),
            SemanticDedupStrategyHandler(),
            HybridStrategyHandler(),
        ]
        return registry

    def register(self, handler: CompressionStrategyHandler) -> None:
        """Register a new strategy handler."""
        self._handlers.insert(0, handler)

    async def compress(
        self,
        strategy: Any,
        context: Any,
        query: Any,
        kwargs: dict[str, Any],
    ) -> Any:
        """Compress context using the appropriate strategy."""
        for handler in self._handlers:
            if handler.can_handle(strategy):
                return await handler.create_and_compress(
                    strategy,
                    context,
                    query,
                    kwargs,
                )
        msg = f"Unknown compression strategy: {strategy}"
        raise ValueError(msg)
