"""Token-based chunking strategy."""

from __future__ import annotations

from typing import Any

from lexigram.ai.rag.chunking.base import AbstractChunker
from lexigram.ai.rag.chunking.types import Chunk


class TokenChunker(AbstractChunker):
    """Chunking based on token count using tiktoken.

    Example:
        >>> chunker = TokenChunker(chunk_size=512, overlap=50)
        >>> chunks = chunker.chunk("Long text to tokenize...")
    """

    def __init__(
        self,
        chunk_size: int = 512,
        overlap: int = 50,
        encoding_name: str = "cl100k_base",
    ):
        """Initialize token chunker.

        Args:
            chunk_size: Target tokens per chunk
            overlap: Token overlap between chunks
            encoding_name: tiktoken encoding name
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.encoding_name = encoding_name

        try:
            import tiktoken  # type: ignore[import-not-found]

            self.encoding = tiktoken.get_encoding(encoding_name)
        except ImportError as e:
            raise ImportError(
                "Token chunking requires 'tiktoken' package. "
                "Install with: pip install lexigram-intelligence[rag]",
            ) from e

    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        """Split text by tokens.

        Args:
            text: Text to chunk
            metadata: Optional metadata

        Returns:
            List of chunks
        """
        if not text:
            return []

        # Encode text to tokens
        tokens = self.encoding.encode(text)

        # Split into chunks
        chunks: list[Chunk] = []
        start = 0
        chunk_index = 0

        while start < len(tokens):
            # Get chunk tokens
            end = start + self.chunk_size
            chunk_tokens = tokens[start:end]

            # Decode tokens back to text for the chunk
            chunk_text = self.encoding.decode(chunk_tokens)

            # Note: start_index and end_index are character-based in the Chunk model.
            # Calculating precise character indices from tokens is complex with tiktoken.
            # For now, we'll store basic identifiers.
            # If precise mapping is required, more advanced logic would be needed.

            chunks.append(
                Chunk(
                    text=chunk_text,
                    source=metadata.get("source", "unknown") if metadata else "unknown",
                    chunk_index=chunk_index,
                    metadata={
                        **(metadata or {}),
                        "token_count": len(chunk_tokens),
                        "encoding": self.encoding_name,
                    },
                ),
            )

            chunk_index += 1
            # Move to next chunk with overlap
            # If chunk is shorter than overlap, we still move forward by at least 1
            start = max(start + 1, end - self.overlap)

        return chunks
