"""Fixed-size chunking strategy."""

from __future__ import annotations

from typing import Any

from lexigram.ai.rag.chunking.base import AbstractChunker
from lexigram.ai.rag.chunking.types import Chunk


class FixedSizeChunker(AbstractChunker):
    """Fixed-size chunking with optional overlap.

    Splits text into chunks of approximately equal size with configurable overlap.

    Example:
        >>> chunker = FixedSizeChunker(chunk_size=500, overlap=50)
        >>> chunks = chunker.chunk("Long text...")
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        overlap: int = 200,
        separator: str = " ",
        keep_separator: bool = True,
    ):
        """Initialize fixed-size chunker.

        Args:
            chunk_size: Target size of each chunk in characters
            overlap: Number of overlapping characters between chunks
            separator: Character/string to split on (default: space)
            keep_separator: Whether to keep separator in chunks
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.separator = separator
        self.keep_separator = keep_separator

        if overlap >= chunk_size:
            msg = "overlap must be less than chunk_size"
            raise ValueError(msg)

    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        """Split text into fixed-size chunks.

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
        step = self.chunk_size - self.overlap

        if step <= 0:
            step = 1  # Prevent infinite loop

        position = 0
        while position < len(text):
            end = min(position + self.chunk_size, len(text))
            chunk_text = text[position:end]

            if chunk_text.strip():
                chunks.append(
                    Chunk(
                        text=chunk_text,
                        start_index=position,
                        end_index=end,
                        chunk_index=chunk_index,
                        metadata=metadata,
                    ),
                )
                chunk_index += 1

            position += step

        return chunks
