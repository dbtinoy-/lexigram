"""Token limit compression strategies."""

from __future__ import annotations

from datetime import UTC, datetime

from lexigram.ai.rag.context_compression.base import AbstractCompressor
from lexigram.ai.rag.context_compression.types import (
    CompressionResult,
    CompressionStrategy,
)


class TokenLimitCompressor(AbstractCompressor):
    """Simple truncation to token limit.

    Truncates context to fit within token limit, preserving the beginning
    and optionally the end of the text.

    Example:
        >>> compressor = TokenLimitCompressor(
        ...     max_tokens=500,
        ...     preserve_end=True,
        ...     end_ratio=0.2
        ... )
        >>> result = await compressor.compress(very_long_context)
    """

    def __init__(
        self,
        max_tokens: int = 500,
        preserve_end: bool = False,
        end_ratio: float = 0.2,
    ):
        """Initialize token limit compressor.

        Args:
            max_tokens: Maximum tokens to keep.
            preserve_end: Whether to preserve end of text.
            end_ratio: Ratio of tokens to preserve from end (if preserve_end=True).
        """
        self.max_tokens = max_tokens
        self.preserve_end = preserve_end
        self.end_ratio = end_ratio

    async def compress(
        self,
        context: str | list[str],
        query: str | None = None,
        **kwargs,
    ) -> CompressionResult:
        """Compress by truncating to token limit."""
        original_text = self._normalize_context(context)
        original_tokens = self._estimate_tokens(original_text)

        if original_tokens <= self.max_tokens:
            # Already within limit
            compressed_text = original_text
        elif self.preserve_end:
            # Keep beginning and end
            start_tokens = int(self.max_tokens * (1 - self.end_ratio))
            end_tokens = int(self.max_tokens * self.end_ratio)

            # Approximate character counts
            start_chars = start_tokens * 4
            end_chars = end_tokens * 4

            start_text = original_text[:start_chars]
            end_text = original_text[-end_chars:]

            compressed_text = start_text + "\n[...]\n" + end_text
        else:
            # Keep only beginning
            max_chars = self.max_tokens * 4
            compressed_text = original_text[:max_chars]

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
            strategy=CompressionStrategy.TOKEN_LIMIT,
            metadata={
                "max_tokens": self.max_tokens,
                "preserve_end": self.preserve_end,
                "end_ratio": self.end_ratio if self.preserve_end else 0.0,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
