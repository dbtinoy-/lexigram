"""Recursive chunking strategy."""

from __future__ import annotations

import re
from typing import Any

from lexigram.ai.rag.chunking.base import AbstractChunker
from lexigram.ai.rag.chunking.types import Chunk


class RecursiveChunker(AbstractChunker):
    """Recursive chunking using multiple separators.

    Tries to split on separators in order of preference (e.g., paragraphs, then
    sentences, then words) to maintain semantic coherence.

    Example:
        >>> chunker = RecursiveChunker(
        ...     chunk_size=1000,
        ...     separators=[r'\\n\\n', r'\\n', r'\\. ', r' ']
        ... )
        >>> chunks = chunker.chunk("Document text...")
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        overlap: int = 200,
        separators: list[str] | None = None,
        is_regex: bool = True,
    ):
        """Initialize recursive chunker.

        Args:
            chunk_size: Target chunk size in characters
            overlap: Overlap between chunks
            separators: List of separators to try (in order of preference)
            is_regex: Whether separators are regex patterns
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.is_regex = is_regex

        # Default separators: paragraph, line, sentence, word
        self.separators = separators or [
            r"\n\n",  # Paragraph
            r"\n",  # Line
            r"\.\s",  # Sentence (period + space)
            r" ",  # Word
        ]

        if overlap >= chunk_size:
            msg = "overlap must be less than chunk_size"
            raise ValueError(msg)

    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        """Split text recursively.

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
            step = 1

        position = 0
        while position < len(text):
            end = min(position + self.chunk_size, len(text))

            # Try to find a good separator position
            if end < len(text):
                best_split = end
                for sep in self.separators:
                    if self.is_regex:
                        # Find last match of separator before end
                        matches = list(re.finditer(sep, text[position:end]))
                        if matches:
                            best_split = position + matches[-1].end()
                            break
                    else:
                        pos = text.rfind(sep, position, end)
                        if pos > position:
                            best_split = pos + len(sep)
                            break
                end = best_split

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
