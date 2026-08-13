"""Hybrid compression strategies."""

from __future__ import annotations

from datetime import UTC, datetime

from lexigram.ai.rag.context_compression.base import AbstractCompressor
from lexigram.ai.rag.context_compression.types import (
    CompressionResult,
    CompressionStrategy,
)


class HybridCompressor(AbstractCompressor):
    """Combine multiple compression strategies.

    Applies multiple compressors in sequence for maximum compression
    while maintaining quality.

    Example:
        >>> compressor = HybridCompressor(
        ...     compressors=[
        ...         SemanticDeduplicationCompressor(),
        ...         ExtractiveSummaryCompressor(max_sentences=10),
        ...         TokenLimitCompressor(max_tokens=500),
        ...     ]
        ... )
        >>> result = await compressor.compress(very_long_context, query="...")
    """

    def __init__(self, compressors: list[AbstractCompressor]):
        """Initialize hybrid compressor.

        Args:
            compressors: List of compressors to apply in sequence.
        """
        self.compressors = compressors

    async def compress(
        self,
        context: str | list[str],
        query: str | None = None,
        **kwargs,
    ) -> CompressionResult:
        """Compress using multiple strategies in sequence."""
        original_text = self._normalize_context(context)
        original_tokens = self._estimate_tokens(original_text)

        current_text = original_text
        intermediate_results = []

        # Apply each compressor in sequence
        for _i, compressor in enumerate(self.compressors):
            result = await compressor.compress(current_text, query=query, **kwargs)
            current_text = result.compressed_text
            intermediate_results.append(
                {
                    "compressor": compressor.__class__.__name__,
                    "strategy": result.strategy.value,
                    "compression_ratio": result.compression_ratio,
                    "tokens": result.compressed_tokens,
                },
            )

        compressed_text = current_text
        compressed_tokens = self._estimate_tokens(compressed_text)
        compression_ratio = (
            compressed_tokens / original_tokens if original_tokens > 0 else 1.0
        )

        return CompressionResult(
            original_text=original_text,
            compressed_text=compressed_text,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compression_ratio,
            strategy=CompressionStrategy.HYBRID,
            metadata={
                "num_compressors": len(self.compressors),
                "intermediate_results": intermediate_results,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
