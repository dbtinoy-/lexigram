"""Type definitions for RAG module."""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.ai.rag.chunking.types import Chunk
from lexigram.ai.rag.exceptions import RAGError
from lexigram.contracts.ai.vector import Document
from lexigram.contracts.core import Metadata
from lexigram.domain import DomainModel
from lexigram.validation import Field


@dataclass(init=False)
class Context(DomainModel):
    """Retrieved context for RAG generation.

    Example:
        >>> context = Context(
        ...     query="What is Lexigram?",
        ...     documents=[doc1, doc2],
        ...     metadata={"retrieval_time": 0.123}
        ... )
    """

    query: str = Field(description="Original query")
    documents: list[Document] = Field(description="Retrieved context documents")
    metadata: Metadata = Field(default_factory=dict, description="Context metadata")


__all__ = ["Chunk", "Context", "RAGError"]
