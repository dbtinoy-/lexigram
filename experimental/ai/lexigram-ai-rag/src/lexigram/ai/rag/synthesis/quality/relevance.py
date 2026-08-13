"""Relevance filter for response quality.

This module implements relevance filtering to verify that synthesized
responses answer the original query.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.contracts.ai import EmbeddingClientProtocol

from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class RelevanceFilter:
    """Filter responses by relevance to query.

    This component checks if the response actually answers the query.

    Attributes:
        threshold: Relevance threshold (0-1)
        embedding_client: Optional embedding client for semantic similarity
    """

    def __init__(
        self,
        threshold: float = 0.6,
        embedding_client: EmbeddingClientProtocol | None = None,
    ):
        """Initialize the relevance filter.

        Args:
            threshold: Relevance threshold
            embedding_client: Optional embedding client for semantic check
        """
        self.threshold = threshold
        self.embedding_client = embedding_client

    def _extract_keywords(self, text: str) -> set[str]:
        """Extract keywords from text.

        Args:
            text: Input text

        Returns:
            Set of keywords
        """
        words = re.findall(r"\b\w+\b", text.lower())

        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "as",
            "is",
            "was",
            "are",
            "been",
            "be",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
        }

        return {w for w in words if w not in stop_words and len(w) > 2}

    async def check_relevance(
        self,
        query: str,
        response: str,
    ) -> float:
        """Check response relevance to query.

        Args:
            query: The original query
            response: The synthesized response

        Returns:
            Relevance score (0-1)
        """
        if not query or not response:
            return 0.0

        # If embedding client available, use semantic similarity
        if self.embedding_client:
            try:
                query_emb = await self.embedding_client.embed([query])
                response_emb = await self.embedding_client.embed([response])

                # Cosine similarity
                import numpy as np

                similarity = float(
                    np.dot(query_emb, response_emb)
                    / (np.linalg.norm(query_emb) * np.linalg.norm(response_emb)),
                )
                return max(0.0, min(1.0, similarity))
            except (ValueError, TypeError, RuntimeError) as e:
                logger.debug("Embedding similarity failed: %s", e)
                # Fall back to keyword matching

        # Keyword-based relevance
        query_keywords = self._extract_keywords(query)
        response_keywords = self._extract_keywords(response)

        if not query_keywords:
            return 1.0

        overlap = len(query_keywords & response_keywords)
        return overlap / len(query_keywords)

    async def is_relevant(
        self,
        query: str,
        response: str,
    ) -> bool:
        """Check if response meets relevance threshold.

        Args:
            query: The original query
            response: The synthesized response

        Returns:
            True if response is relevant
        """
        score = await self.check_relevance(query, response)
        return score >= self.threshold
