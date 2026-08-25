"""Base document loader abstraction for RAG."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.ai.rag.chunking.types import Chunk


class AbstractDocumentLoader:
    """Base class for document loaders."""

    async def load(self, source: str | Path) -> list[Chunk]:
        """Load documents from source.

        Args:
            source: Document source (file path, URL, etc.)

        Returns:
            List of document chunks

        Raises:
            RAGError: If loading fails
        """
        raise NotImplementedError


__all__ = ["AbstractDocumentLoader"]
