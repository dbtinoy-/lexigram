"""Base HyDE generator with common functionality."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from lexigram.ai.rag.hyde.protocols import EmbeddingClientProtocol
from lexigram.ai.rag.hyde.types import HyDEResult, HypotheticalDocument
from lexigram.contracts import (
    ChatMessage,
    LLMClientProtocol,
)


class AbstractHyDEGenerator(ABC):
    """Base class for HyDE generators."""

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        embedding_client: EmbeddingClientProtocol | None = None,
    ):
        """Initialize generator.

        Args:
            llm_client: Client for generating hypothetical documents
            embedding_client: Optional client for generating embeddings
        """
        self.llm_client = llm_client
        self.embedding_client = embedding_client

    @abstractmethod
    async def generate(
        self,
        query: str,
        num_documents: int = 1,
        **kwargs: Any,
    ) -> HyDEResult:
        """Generate hypothetical documents for query.

        Args:
            query: User query
            num_documents: Number of hypothetical documents to generate
            **kwargs: Additional parameters

        Returns:
            HyDE result with hypothetical documents
        """

    def _build_prompt(
        self,
        query: str,
        context: str = "",
        domain: str = "",
    ) -> str:
        """Build prompt for generating hypothetical document.

        Args:
            query: User query
            context: Optional context
            domain: Optional domain specification

        Returns:
            Formatted prompt
        """
        prompt = (
            "Generate a detailed, informative passage that would answer this query:\n\n"
        )
        prompt += f"Query: {query}\n\n"

        if domain:
            prompt += f"Domain: {domain}\n\n"

        if context:
            prompt += f"Context: {context}\n\n"

        prompt += (
            "Write a passage that directly answers this query with specific details, "
            "facts, and relevant information. Do not include the query itself in your response."
        )

        return prompt

    async def _generate_single_document(
        self,
        query: str,
        temperature: float = 0.7,
        max_tokens: int = 200,
        **kwargs: Any,
    ) -> str:
        """Generate a single hypothetical document.

        Args:
            query: User query
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            Generated hypothetical document content
        """
        prompt = self._build_prompt(
            query,
            context=kwargs.get("context", ""),
            domain=kwargs.get("domain", ""),
        )

        messages = [ChatMessage(role="user", content=prompt)]

        result = await self.llm_client.complete(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if result.is_err():
            raise result.unwrap_err()
        response = result.unwrap()

        # Extract content from response
        content = self._extract_content(response)
        return content.strip()

    def _extract_content(self, response: Any) -> str:
        """Extract content from LLM response.

        Args:
            response: LLM response object

        Returns:
            Extracted content string
        """
        # Handle different response formats
        if hasattr(response, "content"):
            return response.content
        if hasattr(response, "text"):
            return response.text
        if hasattr(response, "choices"):
            return response.choices[0].message.content
        if isinstance(response, str):
            return response
        return str(response)

    async def _embed_documents(
        self,
        documents: list[HypotheticalDocument],
    ) -> list[list[float]]:
        """Generate embeddings for hypothetical documents.

        Args:
            documents: List of hypothetical documents

        Returns:
            List of embeddings
        """
        if not self.embedding_client:
            msg = "Embedding client required for embedding documents"
            raise ValueError(msg)

        texts = [doc.content for doc in documents]
        return await self.embedding_client.embed(texts)

    def _aggregate_embeddings(
        self,
        embeddings: list[list[float]],
        weights: list[float] | None = None,
    ) -> list[float]:
        """Aggregate multiple embeddings into one.

        Args:
            embeddings: List of embedding vectors
            weights: Optional weights for each embedding

        Returns:
            Aggregated embedding vector
        """
        if not embeddings:
            return []

        if weights is None:
            weights = [1.0] * len(embeddings)

        # Normalize weights
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        # Weighted average
        embedding_dim = len(embeddings[0])
        aggregated = [0.0] * embedding_dim

        for embedding, weight in zip(embeddings, normalized_weights, strict=False):
            for i, val in enumerate(embedding):
                aggregated[i] += val * weight

        # Normalize vector
        magnitude = sum(x * x for x in aggregated) ** 0.5
        if magnitude > 0:
            aggregated = [x / magnitude for x in aggregated]

        return aggregated
