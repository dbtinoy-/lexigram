"""Sliding window chunking strategy."""

from __future__ import annotations

from typing import Any

from lexigram.ai.rag.chunking.base import AbstractChunker
from lexigram.ai.rag.chunking.types import Chunk


class SlidingWindowChunker(AbstractChunker):
    """Sliding window chunking with configurable stride.

    Creates overlapping chunks by sliding a window across the text.

    Example:
        >>> chunker = SlidingWindowChunker(window_size=500, stride=250)
        >>> chunks = chunker.chunk("Long document...")
    """

    def __init__(self, window_size: int = 1000, stride: int = 500):
        """Initialize sliding window chunker.

        Args:
            window_size: Size of each window in characters
            stride: Step size for sliding (stride < window_size creates overlap)
        """
        self.window_size = window_size
        self.stride = stride

        if stride <= 0:
            msg = "Stride must be positive"
            raise ValueError(msg)
        if stride > window_size:
            msg = "Stride should not exceed window_size"
            raise ValueError(msg)

    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        """Split text using sliding window.

        Args:
            text: Text to chunk
            metadata: Optional metadata

        Returns:
            List of chunks
        """
        if not text:
            return []

        chunks: list[Chunk] = []
        chunk_index = 0

        for start in range(0, len(text), self.stride):
            end = min(start + self.window_size, len(text))
            chunk_text = text[start:end]

            if chunk_text.strip():
                chunks.append(
                    Chunk(
                        text=chunk_text,
                        start_index=start,
                        end_index=end,
                        chunk_index=chunk_index,
                        metadata=metadata,
                    ),
                )
                chunk_index += 1

            # Stop if we've reached the end
            if end >= len(text):
                break

        return chunks
