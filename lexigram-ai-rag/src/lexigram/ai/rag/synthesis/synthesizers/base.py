"""Base synthesizer protocol and abstract base class.

This module defines the internal protocol that all response synthesizers must
implement, and the abstract base class that bridges to the contracts-level
``SynthesizerProtocol`` by converting ``SearchResultProtocol`` items to
internal ``ContextChunk`` objects.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Protocol

from lexigram.ai.rag.synthesis.types import ContextChunk, SynthesisResult
from lexigram.contracts.ai.exceptions import RAGError
from lexigram.contracts.ai.rag import RAGResponse, SynthesisError
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.ai.vector import SearchResultProtocol


class ResponseSynthesizerProtocol(Protocol):
    """Protocol for internal response synthesizers.

    All synthesizer implementations must provide an async
    ``_synthesize_internal`` method that takes a query and context chunks
    and returns a :class:`SynthesisResult`.
    """

    async def _synthesize_internal(
        self,
        query: str,
        context_chunks: list[ContextChunk],
        **kwargs: Any,
    ) -> SynthesisResult:
        """Synthesize a response from query and context chunks.

        Args:
            query: The user query.
            context_chunks: Retrieved context chunks.
            **kwargs: Additional synthesis parameters.

        Returns:
            SynthesisResult with the synthesized response and metadata.

        Raises:
            ValueError: If query is empty or no context chunks provided.
        """
        ...


class AbstractSynthesizer(ABC):
    """Abstract base providing a contracts-conformant ``synthesize()`` method.

    Subclasses implement :meth:`_synthesize_internal` with the internal
    ``ContextChunk``-based signature.  This class bridges to the contracts
    ``SynthesizerProtocol`` by converting ``SearchResultProtocol`` items to
    ``ContextChunk`` objects and wrapping the result in
    ``Result[RAGResponse, RAGError]``.
    """

    def _to_context_chunk(self, result: SearchResultProtocol) -> ContextChunk:
        """Convert a ``SearchResultProtocol`` to an internal ``ContextChunk``.

        Args:
            result: The search result to convert.

        Returns:
            An internal ContextChunk populated from the search result.
        """
        doc = result.document
        source = doc.id or "unknown"
        score = max(0.0, min(1.0, float(result.score)))
        return ContextChunk(
            text=doc.text,
            source=source,
            score=score,
            metadata=dict(result.metadata),
        )

    async def synthesize(
        self,
        query: str,
        context: list[SearchResultProtocol],
        **kwargs: Any,
    ) -> Result[RAGResponse, RAGError]:
        """Synthesize an answer conforming to ``SynthesizerProtocol``.

        Converts ``SearchResultProtocol`` items to internal ``ContextChunk``
        objects, delegates to :meth:`_synthesize_internal`, and wraps the
        outcome in ``Result[RAGResponse, RAGError]``.

        Args:
            query: The user query.
            context: Search results providing context.
            **kwargs: Additional synthesis parameters forwarded to the
                internal implementation.

        Returns:
            ``Ok(RAGResponse)`` on success, ``Err(RAGError)`` on failure.
        """
        try:
            chunks = [self._to_context_chunk(sr) for sr in context]
            internal = await self._synthesize_internal(query, chunks, **kwargs)
            confidence: float | None = (
                internal.quality_metrics.confidence
                if internal.quality_metrics
                else None
            )
            return Ok(
                RAGResponse(
                    answer=internal.response,
                    sources=list(context),
                    citations=internal.citations or None,
                    confidence=confidence,
                )
            )
        except RAGError as exc:
            return Err(exc)
        except Exception as exc:
            return Err(SynthesisError(str(exc)))

    @abstractmethod
    async def _synthesize_internal(
        self,
        query: str,
        context_chunks: list[ContextChunk],
        **kwargs: Any,
    ) -> SynthesisResult:
        """Perform internal synthesis from context chunks.

        Args:
            query: The user query.
            context_chunks: Retrieved context chunks.
            **kwargs: Additional synthesis parameters.

        Returns:
            SynthesisResult with the synthesized response and metadata.

        Raises:
            ValueError: If query is empty or no context chunks provided.
        """
        ...
