"""Direct synthesizer implementation.

This module implements a simple direct concatenation synthesizer that combines
context chunks with minimal processing.
"""

from __future__ import annotations

from lexigram.ai.rag.synthesis.synthesizers.base import AbstractSynthesizer
from lexigram.ai.rag.synthesis.types import (
    ContextChunk,
    SynthesisResult,
    SynthesisStrategy,
)


class DirectSynthesizer(AbstractSynthesizer):
    """Direct concatenation synthesizer.

    This synthesizer simply concatenates context chunks with minimal processing.
    It's the fastest approach but may produce less coherent responses.

    Attributes:
        separator: Separator between chunks (default: double newline)
        max_chunks: Maximum number of chunks to include (None = all)
        include_sources: Whether to include source citations
    """

    def __init__(
        self,
        separator: str = "\n\n",
        max_chunks: int | None = None,
        include_sources: bool = True,
    ):
        """Initialize the direct synthesizer.

        Args:
            separator: Separator between chunks
            max_chunks: Maximum number of chunks to include
            include_sources: Whether to include source citations
        """
        self.separator = separator
        self.max_chunks = max_chunks
        self.include_sources = include_sources

    async def _synthesize_internal(
        self,
        query: str,
        context_chunks: list[ContextChunk],
        **kwargs,
    ) -> SynthesisResult:
        """Synthesize response by concatenating context chunks.

        Args:
            query: The user query
            context_chunks: Retrieved context chunks
            **kwargs: Additional parameters (ignored)

        Returns:
            SynthesisResult with concatenated response

        Raises:
            ValueError: If query is empty or no context chunks provided
        """
        if not query:
            msg = "Query cannot be empty"
            raise ValueError(msg)
        if not context_chunks:
            msg = "No context chunks provided"
            raise ValueError(msg)

        # Sort by rank (or score if rank not set)
        sorted_chunks = sorted(
            context_chunks,
            key=lambda c: c.rank if c.rank is not None else -c.score,
        )

        # Limit number of chunks if specified
        chunks_to_use = (
            sorted_chunks[: self.max_chunks] if self.max_chunks else sorted_chunks
        )

        # Build response text
        response_parts: list[str] = []

        for i, chunk in enumerate(chunks_to_use, 1):
            if self.include_sources:
                response_parts.append(f"[{i}] {chunk.text}")
            else:
                response_parts.append(chunk.text)

        response = self.separator.join(response_parts)

        # Build citations if sources included
        citations = []
        if self.include_sources:
            citations = [
                {
                    "number": i,
                    "source": chunk.source,
                    "score": chunk.score,
                    "metadata": chunk.metadata,
                }
                for i, chunk in enumerate(chunks_to_use, 1)
            ]

        return SynthesisResult(
            query=query,
            response=response,
            strategy=SynthesisStrategy.DIRECT,
            context_chunks=chunks_to_use,
            citations=citations,
            metadata={
                "num_chunks": len(chunks_to_use),
                "separator": self.separator,
                "include_sources": self.include_sources,
            },
        )
