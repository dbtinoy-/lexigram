"""Single HyDE generator implementation."""

from __future__ import annotations

from typing import Any

from lexigram.ai.rag.hyde.base import AbstractHyDEGenerator
from lexigram.ai.rag.hyde.protocols import EmbeddingClientProtocol
from lexigram.ai.rag.hyde.types import HyDEResult, HyDEStrategy, HypotheticalDocument
from lexigram.contracts import (
    LLMClientProtocol,
)


class SingleHyDEGenerator(AbstractHyDEGenerator):
    """Generator for single hypothetical document."""

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        embedding_client: EmbeddingClientProtocol | None = None,
        temperature: float = 0.7,
        max_tokens: int = 200,
    ):
        """Initialize single HyDE generator.

        Args:
            llm_client: Client for generating hypothetical documents
            embedding_client: Optional client for generating embeddings
            temperature: Sampling temperature for generation
            max_tokens: Maximum tokens per document
        """
        super().__init__(llm_client, embedding_client)
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def generate(
        self,
        query: str,
        num_documents: int = 1,
        **kwargs: Any,
    ) -> HyDEResult:
        """Generate single hypothetical document.

        Args:
            query: User query
            num_documents: Ignored (always generates 1)
            **kwargs: Additional parameters (context, domain)

        Returns:
            HyDE result with single hypothetical document
        """
        content = await self._generate_single_document(
            query,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            **kwargs,
        )

        doc = HypotheticalDocument(
            content=content,
            query=query,
            confidence=1.0,
            metadata={
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            },
        )

        # Generate embedding if client available
        aggregated_embedding = None
        if self.embedding_client:
            embeddings = await self._embed_documents([doc])
            aggregated_embedding = embeddings[0] if embeddings else None

        return HyDEResult(
            query=query,
            hypothetical_docs=[doc],
            strategy=HyDEStrategy.SINGLE,
            aggregated_embedding=aggregated_embedding,
            metadata={
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            },
        )
