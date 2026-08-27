"""Document chunker — splits documents into chunks for indexing."""

from __future__ import annotations

from typing import Any


class DocumentChunker:
    """Splits documents into chunks for indexing.

    Demonstrates document preprocessing patterns for RAG pipelines.
    """

    def __init__(self, chunk_size: int = 500) -> None:
        self._chunk_size = chunk_size

    def chunk(
        self, content: str, metadata: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Split content into chunks."""
        chunks = []
        words = content.split()
        current_chunk: list[str] = []
        current_length = 0

        for word in words:
            word_length = len(word) + 1  # +1 for space
            if current_length + word_length > self._chunk_size and current_chunk:
                chunks.append(
                    {
                        "content": " ".join(current_chunk),
                        "metadata": {
                            **(metadata or {}),
                            "chunk_index": len(chunks),
                        },
                    }
                )
                current_chunk = []
                current_length = 0

            current_chunk.append(word)
            current_length += word_length

        if current_chunk:
            chunks.append(
                {
                    "content": " ".join(current_chunk),
                    "metadata": {
                        **(metadata or {}),
                        "chunk_index": len(chunks),
                    },
                }
            )

        return chunks

    def chunk_document(self, doc: dict[str, Any]) -> list[dict[str, Any]]:
        """Chunk a document dict."""
        return self.chunk(doc.get("content", ""), doc.get("metadata", {}))
