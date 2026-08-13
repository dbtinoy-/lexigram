"""Extractive synthesizer implementation.

This module implements an extractive synthesizer that selects and ranks
relevant sentences from context chunks to build a response.
"""

from __future__ import annotations

import re

from lexigram.ai.rag.synthesis.synthesizers.base import AbstractSynthesizer
from lexigram.ai.rag.synthesis.types import (
    ContextChunk,
    SynthesisResult,
    SynthesisStrategy,
)


class ExtractiveSynthesizer(AbstractSynthesizer):
    """Extractive sentence-based synthesizer.

    This synthesizer extracts the most relevant sentences from context chunks
    using scoring methods like TF-IDF, keyword matching, and position.

    Attributes:
        max_sentences: Maximum number of sentences to extract
        min_sentence_length: Minimum sentence length in characters
        use_query_keywords: Whether to boost sentences with query keywords
        reorder_sentences: Whether to reorder for coherence
    """

    def __init__(
        self,
        max_sentences: int = 5,
        min_sentence_length: int = 20,
        use_query_keywords: bool = True,
        reorder_sentences: bool = True,
    ):
        """Initialize the extractive synthesizer.

        Args:
            max_sentences: Maximum number of sentences to extract
            min_sentence_length: Minimum sentence length
            use_query_keywords: Whether to use query keyword matching
            reorder_sentences: Whether to reorder for coherence
        """
        self.max_sentences = max_sentences
        self.min_sentence_length = min_sentence_length
        self.use_query_keywords = use_query_keywords
        self.reorder_sentences = reorder_sentences

    def _extract_sentences(self, text: str) -> list[str]:
        """Extract sentences from text.

        Args:
            text: Input text

        Returns:
            List of sentence strings
        """
        # Simple sentence splitting (can be improved with spacy/nltk)
        sentences = re.split(r"[.!?]+\s+", text)
        return [
            s.strip()
            for s in filter(
                lambda s: len(s.strip()) >= self.min_sentence_length,
                sentences,
            )
        ]

    def _extract_keywords(self, text: str) -> set[str]:
        """Extract keywords from text.

        Args:
            text: Input text

        Returns:
            Set of keywords (lowercased, filtered)
        """
        # Simple keyword extraction (can be improved with NLP)
        words = re.findall(r"\b\w+\b", text.lower())

        # Filter stop words
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
            "will",
            "would",
            "should",
            "could",
            "may",
            "might",
            "must",
            "can",
            "this",
            "that",
            "these",
            "those",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
            "what",
            "which",
            "who",
            "when",
            "where",
            "why",
            "how",
        }

        return {w for w in words if w not in stop_words and len(w) > 2}

    def _score_sentence(
        self,
        sentence: str,
        query_keywords: set[str],
        position: int,
        total_sentences: int,
    ) -> float:
        """Score a sentence for relevance.

        Args:
            sentence: The sentence to score
            query_keywords: Keywords from the query
            position: Position in original text (0-based)
            total_sentences: Total number of sentences

        Returns:
            Relevance score (higher is better)
        """
        score = 0.0

        # Length score (prefer moderate length)
        length = len(sentence)
        if 50 <= length <= 200:
            score += 1.0
        elif 20 <= length < 50 or 200 < length <= 300:
            score += 0.5

        # Keyword matching score
        if self.use_query_keywords and query_keywords:
            sentence_words = set(re.findall(r"\b\w+\b", sentence.lower()))
            keyword_overlap = len(sentence_words & query_keywords)
            score += keyword_overlap * 2.0

        # Position score (early sentences often more relevant)
        position_score = 1.0 - (position / max(total_sentences, 1))
        score += position_score * 0.5

        return score

    async def _synthesize_internal(
        self,
        query: str,
        context_chunks: list[ContextChunk],
        **kwargs,
    ) -> SynthesisResult:
        """Synthesize response by extracting relevant sentences.

        Args:
            query: The user query
            context_chunks: Retrieved context chunks
            **kwargs: Additional parameters

        Returns:
            SynthesisResult with extracted sentences

        Raises:
            ValueError: If query is empty or no context chunks provided
        """
        if not query:
            msg = "Query cannot be empty"
            raise ValueError(msg)
        if not context_chunks:
            msg = "No context chunks provided"
            raise ValueError(msg)

        # Extract query keywords
        query_keywords = self._extract_keywords(query)

        # Extract and score sentences from all chunks
        scored_sentences: list[tuple[str, float, ContextChunk, int]] = []

        for chunk in context_chunks:
            sentences = self._extract_sentences(chunk.text)

            for pos, sentence in enumerate(sentences):
                score = self._score_sentence(
                    sentence,
                    query_keywords,
                    pos,
                    len(sentences),
                )
                # Boost by chunk relevance score
                final_score = score * (chunk.score if chunk.score else 1.0)
                scored_sentences.append((sentence, final_score, chunk, pos))

        # Sort by score and select top sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        top_sentences = scored_sentences[: self.max_sentences]

        # Reorder for coherence if requested
        if self.reorder_sentences:
            # Group by chunk and sort by position within chunk
            top_sentences.sort(key=lambda x: (x[2].rank, x[3]))

        # Build response
        response_sentences = [s[0] for s in top_sentences]
        response = " ".join(response_sentences)

        # Track which chunks were used (deduplicate by source)
        chunks_dict = {}
        for s in top_sentences:
            chunk = s[2]
            if chunk.source not in chunks_dict:
                chunks_dict[chunk.source] = chunk
        chunks_used = list(chunks_dict.values())

        # Build citations
        citations = [
            {
                "source": chunk.source,
                "score": chunk.score,
                "sentences_extracted": sum(1 for s in top_sentences if s[2] == chunk),
            }
            for chunk in chunks_used
        ]

        return SynthesisResult(
            query=query,
            response=response,
            strategy=SynthesisStrategy.EXTRACTIVE,
            context_chunks=chunks_used,
            citations=citations,
            metadata={
                "num_sentences": len(response_sentences),
                "total_candidates": len(scored_sentences),
                "query_keywords": list(query_keywords),
                "reordered": self.reorder_sentences,
            },
        )
