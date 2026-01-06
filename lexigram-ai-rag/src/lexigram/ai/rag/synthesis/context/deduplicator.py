"""Context deduplicator for synthesis.

This module implements context deduplication to remove redundant chunks
before synthesis.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.contracts.ai import EmbeddingClientProtocol

from lexigram.ai.rag.synthesis.types import ContextChunk


class ContextDeduplicator:
    """Remove redundant context chunks.

    This component identifies and removes duplicate or highly similar chunks
    to reduce redundancy and token usage.

    Attributes:
        similarity_threshold: Threshold for considering chunks similar (0-1)
        use_embeddings: Whether to use embeddings for similarity
        embedding_client: Optional embedding client
    """

    def __init__(
        self,
        similarity_threshold: float = 0.9,
        use_embeddings: bool = False,
        embedding_client: EmbeddingClientProtocol | None = None,
    ):
        """Initialize the context deduplicator.

        Args:
            similarity_threshold: Similarity threshold
            use_embeddings: Whether to use embeddings
            embedding_client: Optional embedding client
        """
        self.similarity_threshold = similarity_threshold
        self.use_embeddings = use_embeddings
        self.embedding_client = embedding_client

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using simple overlap.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0-1)
        """
        # Simple word-based Jaccard similarity
        import re

        words1 = set(re.findall(r"\b\w+\b", text1.lower()))
        words2 = set(re.findall(r"\b\w+\b", text2.lower()))

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    async def deduplicate_chunks(
        self,
        chunks: list[ContextChunk],
    ) -> list[ContextChunk]:
        """Remove duplicate chunks.

        Args:
            chunks: Chunks to deduplicate

        Returns:
            Deduplicated list of chunks
        """
        if not chunks:
            return []

        unique_chunks: list[ContextChunk] = []
        seen_texts: set[str] = set()

        for chunk in chunks:
            # Check exact duplicates
            if chunk.text in seen_texts:
                continue

            # Check similarity to existing chunks
            is_duplicate = False

            for unique_chunk in unique_chunks:
                similarity = self._calculate_text_similarity(
                    chunk.text,
                    unique_chunk.text,
                )

                if similarity >= self.similarity_threshold:
                    # Keep the one with higher score
                    chunk_score = chunk.score if chunk.score is not None else 0.0
                    unique_score = (
                        unique_chunk.score if unique_chunk.score is not None else 0.0
                    )
                    if chunk_score > unique_score:
                        unique_chunks.remove(unique_chunk)
                        seen_texts.discard(unique_chunk.text)
                    else:
                        is_duplicate = True
                        break

            if not is_duplicate:
                unique_chunks.append(chunk)
                seen_texts.add(chunk.text)

        return unique_chunks
