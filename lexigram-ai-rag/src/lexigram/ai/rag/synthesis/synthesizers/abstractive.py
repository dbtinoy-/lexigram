"""Abstractive synthesizer implementation.

This module implements an LLM-based abstractive synthesizer that generates
new responses from context chunks.
"""

from __future__ import annotations

from lexigram.ai.rag.synthesis.synthesizers.base import AbstractSynthesizer
from lexigram.ai.rag.synthesis.types import (
    ContextChunk,
    SynthesisResult,
    SynthesisStrategy,
)
from lexigram.contracts import (
    LLMClientProtocol,
)
from lexigram.contracts.ai.llm import ChatMessage, Role


class AbstractiveSynthesizer(AbstractSynthesizer):
    """LLM-based abstractive synthesizer.

    This synthesizer uses an LLM to generate a new response based on the
    retrieved context chunks and query.

    Attributes:
        llm_client: LLM client for generation
        max_context_chunks: Maximum number of chunks to include
        include_citations: Whether to ask for citations
        temperature: LLM temperature (0-1)
    """

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        max_context_chunks: int = 5,
        include_citations: bool = True,
        temperature: float = 0.3,
    ):
        """Initialize the abstractive synthesizer.

        Args:
            llm_client: LLM client implementing LLMClientProtocol protocol
            max_context_chunks: Maximum context chunks to use
            include_citations: Whether to include citations
            temperature: LLM temperature for generation
        """
        self.llm_client = llm_client
        self.max_context_chunks = max_context_chunks
        self.include_citations = include_citations
        self.temperature = temperature

    def _build_prompt(
        self,
        query: str,
        context_chunks: list[ContextChunk],
    ) -> str:
        """Build the synthesis prompt.

        Args:
            query: The user query
            context_chunks: Context chunks to use

        Returns:
            Formatted prompt string
        """
        # Limit chunks
        chunks_to_use = context_chunks[: self.max_context_chunks]

        # Build context section
        context_parts = []
        for i, chunk in enumerate(chunks_to_use, 1):
            context_parts.append(f"[{i}] {chunk.text}")
            if chunk.source:
                context_parts.append(f"   Source: {chunk.source}")

        context_text = "\n\n".join(context_parts)

        # Build prompt
        prompt = f"""You are a helpful assistant that answers questions based on provided context.

Context:
{context_text}

Question: {query}

Instructions:
- Answer the question using ONLY information from the provided context
- Be concise and accurate
- If the context doesn't contain enough information, say so
- Do not make up or infer information not present in the context"""

        if self.include_citations:
            prompt += "\n- Cite sources using [1], [2], etc. when referring to specific information"

        prompt += "\n\nAnswer:"

        return prompt

    async def _synthesize_internal(
        self,
        query: str,
        context_chunks: list[ContextChunk],
        **kwargs,
    ) -> SynthesisResult:
        """Synthesize response using LLM.

        Args:
            query: The user query
            context_chunks: Retrieved context chunks
            **kwargs: Additional parameters (e.g., temperature)

        Returns:
            SynthesisResult with LLM-generated response

        Raises:
            ValueError: If query is empty or no context chunks provided
        """
        if not query:
            msg = "Query cannot be empty"
            raise ValueError(msg)
        if not context_chunks:
            msg = "No context chunks provided"
            raise ValueError(msg)

        # Build prompt
        prompt = self._build_prompt(query, context_chunks)

        # Get temperature from kwargs or use default
        temperature = kwargs.get("temperature", self.temperature)

        # Generate response using LLM
        messages = [ChatMessage(role=Role.USER, content=prompt)]

        try:
            result = await self.llm_client.complete(
                messages,
                temperature=temperature,
                max_tokens=kwargs.get("max_tokens", 500),
            )
            if result.is_err():
                raise result.unwrap_err()
            response = result.unwrap()
        except Exception as e:
            msg = f"LLM generation failed: {e}"
            raise RuntimeError(msg) from e

        response_text_str = response.content

        # Extract citations if included
        citations = []
        if self.include_citations:
            # Simple citation extraction (can be improved)
            import re

            citation_pattern = r"\[(\d+)\]"
            cited_numbers = set(re.findall(citation_pattern, response_text_str))

            for num_str in cited_numbers:
                num = int(num_str)
                if 1 <= num <= len(context_chunks):
                    chunk = context_chunks[num - 1]
                    citations.append(
                        {
                            "number": num,
                            "source": chunk.source,
                            "score": chunk.score,
                        },
                    )

        # Determine which chunks were actually used
        chunks_used = context_chunks[: self.max_context_chunks]

        return SynthesisResult(
            query=query,
            response=response_text_str.strip(),
            strategy=SynthesisStrategy.ABSTRACTIVE,
            context_chunks=chunks_used,
            citations=citations,
            metadata={
                "num_chunks_provided": len(chunks_used),
                "temperature": temperature,
                "include_citations": self.include_citations,
                "prompt_length": len(prompt),
            },
        )
