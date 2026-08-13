"""Custom chunking strategy."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from lexigram.ai.rag.chunking.base import AbstractChunker
from lexigram.ai.rag.chunking.types import Chunk


class CustomChunker(AbstractChunker):
    """Custom chunking using a user-defined function.

    Example:
        >>> def my_splitter(text: str) -> list[str]:
        ...     return text.split("---")
        >>> chunker = CustomChunker(split_fn=my_splitter)
        >>> chunks = chunker.chunk("Part 1---Part 2---Part 3")
    """

    def __init__(self, split_fn: Callable[[str], list[str]]):
        """Initialize custom chunker.

        Args:
            split_fn: Function that takes text and returns list of chunk strings
        """
        self.split_fn = split_fn

    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        """Split text using custom function.

        Args:
            text: Text to chunk
            metadata: Optional metadata

        Returns:
            List of chunks
        """
        if not text:
            return []

        chunk_strings = self.split_fn(text)
        chunks: list[Chunk] = []
        offset = 0

        for i, chunk_text in enumerate(chunk_strings):
            # Find this chunk's position in original text
            start = text.find(chunk_text, offset)
            if start == -1:
                # Chunk not found, use offset
                start = offset

            end = start + len(chunk_text)

            if chunk_text.strip():
                chunks.append(
                    Chunk(
                        text=chunk_text,
                        start_index=start,
                        end_index=end,
                        chunk_index=i,
                        metadata=metadata,
                    ),
                )

            offset = end

        return chunks
