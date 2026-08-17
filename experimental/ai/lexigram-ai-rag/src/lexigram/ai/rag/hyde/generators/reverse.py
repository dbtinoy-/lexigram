"""Reverse HyDE generator implementation."""

from __future__ import annotations

from typing import Any

from lexigram.ai.rag.hyde.base import AbstractHyDEGenerator
from lexigram.ai.rag.hyde.protocols import EmbeddingClientProtocol
from lexigram.ai.rag.hyde.types import HyDEResult, HyDEStrategy, HypotheticalDocument
from lexigram.contracts import (
    ChatMessage,
    LLMClientProtocol,
)


class ReverseHyDEGenerator(AbstractHyDEGenerator):
    """Reverse HyDE: Generate query from hypothetical document."""

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        embedding_client: EmbeddingClientProtocol | None = None,
        temperature: float = 0.5,
        max_tokens: int = 100,
    ):
        """Initialize reverse HyDE generator.

        Args:
            llm_client: Client for generating queries
            embedding_client: Optional client for generating embeddings
            temperature: Lower temperature for precise queries
            max_tokens: Maximum tokens per query
        """
        super().__init__(llm_client, embedding_client)
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _build_reverse_prompt(self, query: str) -> str:
        """Build prompt for reverse HyDE.

        Args:
            query: Original query

        Returns:
            Prompt for generating document then query
        """
        return (
            "First, write a comprehensive passage that would answer this query. "
            "Then, generate 3-5 related queries that this passage would answer.\n\n"
            f"Original Query: {query}\n\n"
            "Format:\n"
            "Passage: [your passage here]\n"
            "Related Queries:\n"
            "1. [query 1]\n"
            "2. [query 2]\n"
            "..."
        )

    async def generate(
        self,
        query: str,
        num_documents: int = 1,
        **kwargs: Any,
    ) -> HyDEResult:
        """Generate hypothetical document and related queries.

        Args:
            query: User query
            num_documents: Ignored
            **kwargs: Additional parameters

        Returns:
            HyDE result with reverse generation
        """
        prompt = self._build_reverse_prompt(query)
        messages = [ChatMessage(role="user", content=prompt)]

        result = await self.llm_client.complete(
            messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens * 3,  # Need more tokens for passage + queries
        )
        if result.is_err():
            raise result.unwrap_err()
        response = result.unwrap()

        content = self._extract_content(response)

        # Parse passage and queries
        passage, queries = self._parse_reverse_response(content)

        doc = HypotheticalDocument(
            content=passage,
            query=query,
            confidence=1.0,
            metadata={
                "related_queries": queries,
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
            strategy=HyDEStrategy.REVERSE,
            aggregated_embedding=aggregated_embedding,
            metadata={
                "related_queries": queries,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            },
        )

    def _parse_reverse_response(self, content: str) -> tuple[str, list[str]]:
        """Parse reverse HyDE response into passage and queries.

        Args:
            content: LLM response content

        Returns:
            Tuple of (passage, list of queries)
        """
        lines = content.strip().split("\n")

        passage_lines = []
        queries = []
        in_passage = False
        in_queries = False

        for line in lines:
            line_lower = line.lower().strip()

            if line_lower.startswith("passage:"):
                in_passage = True
                in_queries = False
                # Get passage content after "Passage:"
                passage_content = line.split(":", 1)[1].strip()
                if passage_content:
                    passage_lines.append(passage_content)
            elif "related queries" in line_lower or "queries:" in line_lower:
                in_passage = False
                in_queries = True
            elif in_passage:
                passage_lines.append(line.strip())
            elif in_queries and line.strip():
                # Extract query (remove numbering)
                query = line.strip()
                # Remove leading numbers and dots
                query = query.lstrip("0123456789.-) ").strip()
                if query:
                    queries.append(query)

        passage = " ".join(passage_lines)

        return passage, queries
