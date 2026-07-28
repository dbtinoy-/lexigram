"""Multiple HyDE generator implementation."""

from __future__ import annotations

from typing import Any

from lexigram.ai.rag.hyde.base import AbstractHyDEGenerator
from lexigram.ai.rag.hyde.protocols import EmbeddingClientProtocol
from lexigram.ai.rag.hyde.types import HyDEResult, HyDEStrategy, HypotheticalDocument
from lexigram.contracts import (
    LLMClientProtocol,
)


class MultipleHyDEGenerator(AbstractHyDEGenerator):
    """Generator for multiple hypothetical documents."""

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        embedding_client: EmbeddingClientProtocol | None = None,
        temperature: float = 0.9,
        max_tokens: int = 150,
        default_num_documents: int = 3,
    ):
        """Initialize multiple HyDE generator.

        Args:
            llm_client: Client for generating hypothetical documents
            embedding_client: Optional client for generating embeddings
            temperature: Higher temperature for diversity
            max_tokens: Maximum tokens per document
            default_num_documents: Default number of documents
        """
        super().__init__(llm_client, embedding_client)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.default_num_documents = default_num_documents

    async def generate(
        self,
        query: str,
        num_documents: int | None = None,
        **kwargs: Any,
    ) -> HyDEResult:
        """Generate multiple hypothetical documents.

        Args:
            query: User query
            num_documents: Number of documents (default: default_num_documents)
            **kwargs: Additional parameters (context, domain)

        Returns:
            HyDE result with multiple hypothetical documents
        """
        if num_documents is None:
            num_documents = self.default_num_documents

        # Generate multiple documents
        documents = []
        for i in range(num_documents):
            content = await self._generate_single_document(
                query,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                **kwargs,
            )

            doc = HypotheticalDocument(
                content=content,
                query=query,
                confidence=1.0 / (i + 1),  # Decrease confidence for later docs
                metadata={
                    "index": i,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                },
            )
            documents.append(doc)

        # Generate embeddings if client available
        aggregated_embedding = None
        if self.embedding_client:
            embeddings = await self._embed_documents(documents)
            # Average embeddings
            aggregated_embedding = self._aggregate_embeddings(embeddings)

        return HyDEResult(
            query=query,
            hypothetical_docs=documents,
            strategy=HyDEStrategy.MULTIPLE,
            aggregated_embedding=aggregated_embedding,
            metadata={
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "num_documents": num_documents,
            },
        )
