"""Semantic deduplication compression strategies."""

from __future__ import annotations

from datetime import UTC, datetime

from lexigram.ai.rag.context_compression.base import AbstractCompressor
from lexigram.ai.rag.context_compression.types import (
    CompressionResult,
    CompressionStrategy,
)


class SemanticDeduplicationCompressor(AbstractCompressor):
    """Remove semantically redundant information.

    Identifies and removes redundant sentences that convey
    the same information as other sentences.

    Example:
        >>> compressor = SemanticDeduplicationCompressor(
        ...     similarity_threshold=0.8
        ... )
        >>> result = await compressor.compress(context_with_repetition)
    """

    def __init__(
        self,
        similarity_threshold: float = 0.8,
        preserve_first: bool = True,
    ):
        """Initialize semantic deduplication compressor.

        Args:
            similarity_threshold: Threshold for considering sentences similar (0.0 to 1.0).
            preserve_first: Keep first occurrence of similar sentences.
        """
        self.similarity_threshold = similarity_threshold
        self.preserve_first = preserve_first

    async def compress(
        self,
        context: str | list[str],
        query: str | None = None,
        **kwargs,
    ) -> CompressionResult:
        """Compress by removing redundant sentences."""
        original_text = self._normalize_context(context)
        original_tokens = self._estimate_tokens(original_text)

        # Split into sentences
        sentences = self._split_sentences(original_text)

        # Deduplicate
        unique_sentences = self._deduplicate_sentences(sentences)

        # Join unique sentences
        compressed_text = " ".join(unique_sentences)

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
            strategy=CompressionStrategy.SEMANTIC_DEDUP,
            metadata={
                "original_sentences": len(sentences),
                "unique_sentences": len(unique_sentences),
                "removed_duplicates": len(sentences) - len(unique_sentences),
                "similarity_threshold": self.similarity_threshold,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        import re

        sentences = re.split(r"[.!?]+\s+", text)
        return list(map(str.strip, filter(str.strip, sentences)))

    def _deduplicate_sentences(self, sentences: list[str]) -> list[str]:
        """Remove duplicate/similar sentences."""
        unique = []
        seen_fingerprints: set[str] = set()

        for sentence in sentences:
            # Create simple fingerprint (for production, use embeddings)
            fingerprint = self._create_fingerprint(sentence)

            # Check if similar to any seen fingerprint
            is_duplicate = False
            for seen_fp in seen_fingerprints:
                if self._are_similar(fingerprint, seen_fp):
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique.append(sentence)
                seen_fingerprints.add(fingerprint)

        return unique

    def _create_fingerprint(self, sentence: str) -> str:
        """Create sentence fingerprint.

        Simple approach: normalized word set.
        For production, use embeddings.
        """
        # Lowercase and split
        words = sentence.lower().split()

        # Remove stopwords
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
        words = list(filter(lambda w: w not in stopwords, words))

        # Sort for comparison
        return " ".join(sorted(words))

    def _are_similar(self, fp1: str, fp2: str) -> bool:
        """Check if two fingerprints are similar."""
        words1 = set(fp1.split())
        words2 = set(fp2.split())

        if not words1 or not words2:
            return False

        # Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        similarity = intersection / union if union > 0 else 0.0

        return similarity >= self.similarity_threshold
