"""Base classes for document chunking."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from lexigram.ai.rag.chunking.types import Chunk


class AbstractChunker(ABC):
    """Base class for document chunkers."""

    @abstractmethod
    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        """Split text into chunks.

        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to chunks

        Returns:
            List of chunks
        """
