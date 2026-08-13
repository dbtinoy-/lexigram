"""Hybrid synthesizer implementation.

Combines extractive and abstractive approaches for robust synthesis.
"""

from __future__ import annotations

from lexigram.ai.rag.synthesis.synthesizers.abstractive import (
    AbstractiveSynthesizer,
)
from lexigram.ai.rag.synthesis.synthesizers.base import AbstractSynthesizer
from lexigram.ai.rag.synthesis.synthesizers.extractive import (
    ExtractiveSynthesizer,
)
from lexigram.ai.rag.synthesis.types import (
    ContextChunk,
    SynthesisResult,
    SynthesisStrategy,
)
from lexigram.contracts import (
    LLMClientProtocol,
)


class HybridSynthesizer(AbstractSynthesizer):
    """Hybrid extractive + abstractive synthesizer.

    This synthesizer first uses extractive methods to reduce and rank context,
    then uses abstractive generation for the final response.

    Attributes:
        extractive: Extractive synthesizer for context reduction
        abstractive: Abstractive synthesizer for final generation
        extraction_ratio: Ratio of content to extract (0-1)
    """

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        extractive_weight: float = 0.3,
        abstractive_weight: float = 0.7,
        min_extractive_score: float = 0.5,
        extraction_ratio: float = 0.5,
        max_extractive_sentences: int = 5,
    ):
        """Initialize the hybrid synthesizer.

        Args:
            llm_client: LLM client implementing LLMClientProtocol protocol
            extractive_weight: Weight for extractive component (0-1)
            abstractive_weight: Weight for abstractive component (0-1)
            min_extractive_score: Minimum score to use extractive results
            extraction_ratio: Fraction of content to extract before abstraction
            max_extractive_sentences: Max sentences to extract in extractive phase
        """
        self.extractive_weight = extractive_weight
        self.abstractive_weight = abstractive_weight
        self.min_extractive_score = min_extractive_score
        self.extraction_ratio = extraction_ratio

        self.extractive = ExtractiveSynthesizer(
            max_sentences=max_extractive_sentences,
            reorder_sentences=True,
        )
        self.abstractive = AbstractiveSynthesizer(
            llm_client=llm_client,
            temperature=0.3,  # Default temperature
        )

    async def _synthesize_internal(
        self,
        query: str,
        context_chunks: list[ContextChunk],
        **kwargs,
    ) -> SynthesisResult:
        """Synthesize response using hybrid approach.

        Args:
            query: The user query
            context_chunks: Retrieved context chunks
            **kwargs: Additional parameters

        Returns:
            SynthesisResult with hybrid-synthesized response

        Raises:
            ValueError: If query is empty or no context chunks provided
        """
        if not query:
            msg = "Query cannot be empty"
            raise ValueError(msg)
        if not context_chunks:
            msg = "No context chunks provided"
            raise ValueError(msg)

        # Phase 1: Extractive reduction
        # Extract most relevant sentences to reduce context size
        extractive_result = await self.extractive._synthesize_internal(
            query=query,
            context_chunks=context_chunks,
        )

        # Create condensed chunks from extracted content
        condensed_chunk = ContextChunk(
            text=extractive_result.response,
            source="extracted_content",
            score=1.0,
            metadata={
                "num_sentences": extractive_result.metadata.get("num_sentences", 0),
                "original_chunks": len(context_chunks),
            },
        )

        # Phase 2: Abstractive synthesis
        # Use LLM to generate final response from condensed content
        abstractive_result = await self.abstractive._synthesize_internal(
            query=query,
            context_chunks=[condensed_chunk],
            **kwargs,
        )

        # Combine metadata from both phases
        metadata = {
            "extraction_phase": extractive_result.metadata,
            "abstraction_phase": abstractive_result.metadata,
            "original_chunks": len(context_chunks),
            "extractive_weight": self.extractive_weight,
            "abstractive_weight": self.abstractive_weight,
        }

        return SynthesisResult(
            query=query,
            response=abstractive_result.response,
            strategy=SynthesisStrategy.HYBRID,
            context_chunks=extractive_result.context_chunks,  # Original chunks used
            citations=abstractive_result.citations,
            metadata=metadata,
        )
