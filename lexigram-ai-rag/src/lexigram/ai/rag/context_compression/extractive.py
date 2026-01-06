"""Extractive compression strategies."""

from __future__ import annotations

from lexigram.ai.rag.context_compression.base import AbstractCompressor
from lexigram.ai.rag.context_compression.types import (
    CompressionResult,
    CompressionStrategy,
)


class ExtractiveSummaryCompressor(AbstractCompressor):
    """Extract most relevant sentences from context.

    This compressor selects sentences based on:
    - Relevance to query (if provided)
    - Position in document (first/last sentences)
    - Sentence length and informativeness

    Example:
        >>> compressor = ExtractiveSummaryCompressor(
        ...     max_sentences=5,
        ...     query_weight=0.7,
        ...     position_weight=0.3
        ... )
        >>> result = await compressor.compress(
        ...     context=long_text,
        ...     query="What is machine learning?"
        ... )
    """

    def __init__(
        self,
        max_sentences: int = 5,
        query_weight: float = 0.7,
        position_weight: float = 0.3,
        min_sentence_length: int = 20,
    ):
        """Initialize extractive compressor.

        Args:
            max_sentences: Maximum sentences to extract.
            query_weight: Weight for query relevance (0.0 to 1.0).
            position_weight: Weight for sentence position (0.0 to 1.0).
            min_sentence_length: Minimum sentence length in characters.
        """
        self.max_sentences = max_sentences
        self.query_weight = query_weight
        self.position_weight = position_weight
        self.min_sentence_length = min_sentence_length

    async def compress(
        self,
        context: str | list[str],
        query: str | None = None,
        **kwargs,
    ) -> CompressionResult:
        """Compress by extracting most relevant sentences."""
        from datetime import UTC, datetime

        original_text = self._normalize_context(context)
        original_tokens = self._estimate_tokens(original_text)

        # Split into sentences
        sentences = self._split_sentences(original_text)

        # Filter short sentences
        sentences = list(
            filter(lambda s: len(s) >= self.min_sentence_length, sentences),
        )

        if len(sentences) <= self.max_sentences:
            # Already short enough
            compressed_text = original_text
        else:
            # Score and select top sentences
            scored_sentences = self._score_sentences(sentences, query)
            top_sentences = sorted(
                scored_sentences,
                key=lambda x: x[1],
                reverse=True,
            )[: self.max_sentences]

            # Sort by original position to maintain flow
            top_sentences = sorted(top_sentences, key=lambda x: x[2])

            # Join selected sentences
            compressed_text = " ".join(s[0] for s in top_sentences)

        compressed_tokens = self._estimate_tokens(compressed_text)
        compression_ratio = (
            compressed_tokens / original_tokens if original_tokens > 0 else 1.0
        )

        return CompressionResult(
            original_text=original_text,
            compressed_text=compressed_text,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compression_ratio,
            strategy=CompressionStrategy.EXTRACTIVE,
            metadata={
                "total_sentences": len(sentences),
                "selected_sentences": min(len(sentences), self.max_sentences),
                "query_used": query is not None,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences (simple approach)."""
        import re

        # Split on period, exclamation, question mark followed by space/newline
        sentences = re.split(r"[.!?]+\s+", text)
        return list(map(str.strip, filter(str.strip, sentences)))

    def _score_sentences(
        self,
        sentences: list[str],
        query: str | None,
    ) -> list[tuple[str, float, int]]:
        """Score sentences based on relevance and position.

        Returns:
            List of (sentence, score, original_index) tuples.
        """
        scored = []
        total = len(sentences)

        for idx, sentence in enumerate(sentences):
            score = 0.0

            # Position score (first and last sentences are important)
            if idx == 0:
                position_score = 1.0
            elif idx == total - 1:
                position_score = 0.8
            elif idx < total * 0.2:  # First 20%
                position_score = 0.7
            elif idx > total * 0.8:  # Last 20%
                position_score = 0.6
            else:
                position_score = 0.3

            score += position_score * self.position_weight

            # Query relevance score
            if query:
                query_score = self._compute_relevance(sentence, query)
                score += query_score * self.query_weight

            # Length bonus (longer sentences often more informative)
            length_score = min(len(sentence) / 200, 1.0)  # Normalize to 200 chars
            score += length_score * 0.1

            scored.append((sentence, score, idx))

        return scored

    def _compute_relevance(self, sentence: str, query: str) -> float:
        """Compute relevance score between sentence and query.

        Simple approach using word overlap.
        For production, use embeddings or cross-encoder.
        """
        # Lowercase and split into words
        sentence_words = set(sentence.lower().split())
        query_words = set(query.lower().split())

        # Remove common stopwords (simple list)
        stopwords = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "and",
            "or",
            "but",
        }
        sentence_words -= stopwords
        query_words -= stopwords

        if not query_words:
            return 0.0

        # Calculate overlap
        overlap = len(sentence_words & query_words)
        return overlap / len(query_words)
