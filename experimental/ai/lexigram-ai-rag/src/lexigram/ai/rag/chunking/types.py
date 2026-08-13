"""Types and data models for document chunking."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from lexigram.contracts.ai.chunks import Chunk as ChunkBase
from lexigram.domain import DomainModel
from lexigram.validation import Field


@dataclass(init=False, frozen=True)
class Chunk(DomainModel, ChunkBase):
    """A chunk of text with metadata.

    Attributes:
        text: The chunk text content
        source: Source document identifier
        start_index: Starting character position in original document
        end_index: Ending character position in original document
        chunk_index: Sequential index of this chunk
        metadata: Optional metadata dictionary
    """

    text: str = Field(description="Chunk text content")
    source: str = Field(default="unknown", description="Source document identifier")
    score: float | None = Field(default=None, description="Optional retrieval score")
    chunk_index: int = Field(description="Index of this chunk")
    start_index: int | None = Field(
        default=None, description="Starting character position"
    )
    end_index: int | None = Field(default=None, description="Ending character position")
    embedding: list[float] | None = Field(
        default=None, description="Optional embedding associated with the chunk"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")

    def __len__(self) -> int:
        """Get chunk length in characters."""
        return len(self.text)


class ChunkingStrategy(StrEnum):
    """Chunking strategy types."""

    FIXED_SIZE = "fixed_size"  # Fixed character/token count
    RECURSIVE = "recursive"  # Recursive splitting by separators
    SEMANTIC = "semantic"  # Sentence/paragraph boundaries
    SLIDING_WINDOW = "sliding_window"  # Overlapping windows
    TOKEN = "token"  # noqa: S105  # chunking strategy name, not a credential


@dataclass(init=False)
class ChunkingConfig(DomainModel):
    """Configuration for chunking.

    Example:
        >>> config = ChunkingConfig(
        ...     strategy=ChunkingStrategy.FIXED_SIZE,
        ...     chunk_size=1000,
        ...     overlap=200
        ... )
    """

    strategy: ChunkingStrategy = Field(
        default=ChunkingStrategy.FIXED_SIZE,
        description="Chunking strategy to use",
    )
    chunk_size: int = Field(
        default=1000,
        ge=1,
        description="Target chunk size in characters",
    )
    overlap: int = Field(
        default=200,
        ge=0,
        description="Overlap between chunks (for applicable strategies)",
    )
    min_chunk_size: int = Field(
        default=100,
        ge=1,
        description="Minimum chunk size (semantic strategy)",
    )
    separators: list[str] | None = Field(
        default=None,
        description="Separators for recursive chunking",
    )
    encoding_name: str = Field(
        default="cl100k_base",
        description="Tokenizer encoding for token chunking",
    )
