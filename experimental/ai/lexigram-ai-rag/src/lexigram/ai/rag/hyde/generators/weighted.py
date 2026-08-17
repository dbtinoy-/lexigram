"""Weighted HyDE generator implementation."""

from __future__ import annotations

from typing import Any

from lexigram.ai.rag.hyde.base import AbstractHyDEGenerator
from lexigram.ai.rag.hyde.protocols import EmbeddingClientProtocol
from lexigram.ai.rag.hyde.types import HyDEResult, HyDEStrategy, HypotheticalDocument
from lexigram.contracts import (
    LLMClientProtocol,
)


class WeightedHyDEGenerator(AbstractHyDEGenerator):
    """Generator with weighted aggregation of multiple documents."""

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        embedding_client: EmbeddingClientProtocol,
        temperature: float = 0.8,
        max_tokens: int = 150,
        default_num_documents: int = 3,
        confidence_decay: float = 0.7,
    ):
        """Initialize weighted HyDE generator.

        Args:
            llm_client: Client for generating hypothetical documents
            embedding_client: Client for generating embeddings (required)
            temperature: Sampling temperature
            max_tokens: Maximum tokens per document
            default_num_documents: Default number of documents
            confidence_decay: Decay factor for subsequent documents
        """
        super().__init__(llm_client, embedding_client)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.default_num_documents = default_num_documents
        self.confidence_decay = confidence_decay

    async def generate(
        self,
        query: str,
        num_documents: int | None = None,
        **kwargs: Any,
    ) -> HyDEResult:
        """Generate weighted hypothetical documents.

        Args:
            query: User query
            num_documents: Number of documents
            **kwargs: Additional parameters

        Returns:
            HyDE result with weighted aggregation
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

            # Exponential confidence decay
            confidence = self.confidence_decay**i

            doc = HypotheticalDocument(
                content=content,
                query=query,
                confidence=confidence,
                metadata={
                    "index": i,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                },
            )
            documents.append(doc)

        # Generate embeddings (required for weighted strategy)
        embeddings = await self._embed_documents(documents)

        # Weighted aggregation based on confidence
        weights = [doc.confidence for doc in documents]
        aggregated_embedding = self._aggregate_embeddings(embeddings, weights)

        return HyDEResult(
            query=query,
            hypothetical_docs=documents,
            strategy=HyDEStrategy.WEIGHTED,
            aggregated_embedding=aggregated_embedding,
            metadata={
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "num_documents": num_documents,
                "confidence_decay": self.confidence_decay,
                "weights": weights,
            },
        )
