"""Confidence scorer for response quality.

This module implements confidence scoring that combines multiple quality
metrics into an overall confidence score.
"""

from __future__ import annotations

from lexigram.ai.rag.synthesis.quality.faithfulness import FaithfulnessChecker
from lexigram.ai.rag.synthesis.quality.hallucination import (
    HallucinationChecker,
)
from lexigram.ai.rag.synthesis.quality.relevance import RelevanceFilter
from lexigram.ai.rag.synthesis.types import ContextChunk, QualityMetrics


class ConfidenceScorer:
    """Calculate overall confidence score for responses.

    This component combines faithfulness, relevance, and hallucination
    detection into a single confidence score.

    Attributes:
        faithfulness_checker: Component for faithfulness checking
        relevance_filter: Component for relevance filtering
        hallucination_detector: Component for hallucination detection
        weights: Weights for combining scores
    """

    def __init__(
        self,
        faithfulness_checker: FaithfulnessChecker | None = None,
        relevance_filter: RelevanceFilter | None = None,
        hallucination_detector: HallucinationChecker | None = None,
        faithfulness_weight: float = 0.4,
        relevance_weight: float = 0.4,
        coherence_weight: float = 0.2,
    ):
        """Initialize the confidence scorer.

        Args:
            faithfulness_checker: Faithfulness checker instance
            relevance_filter: Relevance filter instance
            hallucination_detector: Hallucination detector instance
            faithfulness_weight: Weight for faithfulness score
            relevance_weight: Weight for relevance score
            coherence_weight: Weight for coherence score
        """
        self.faithfulness_checker = faithfulness_checker or FaithfulnessChecker()
        self.relevance_filter = relevance_filter or RelevanceFilter()
        self.hallucination_detector = hallucination_detector or HallucinationChecker()

        # Normalize weights
        total = faithfulness_weight + relevance_weight + coherence_weight
        self.faithfulness_weight = faithfulness_weight / total
        self.relevance_weight = relevance_weight / total
        self.coherence_weight = coherence_weight / total

    def _calculate_coherence(self, response: str) -> float:
        """Calculate coherence score for response.

        Args:
            response: The response text

        Returns:
            Coherence score (0-1)
        """
        if not response:
            return 0.0

        # Simple heuristics for coherence
        score = 0.5  # Base score

        # Check length (not too short, not too long)
        length = len(response)
        if 50 <= length <= 500:
            score += 0.2
        elif 20 <= length < 50 or 500 < length <= 1000:
            score += 0.1

        # Check sentence structure
        import re

        sentences = re.split(r"[.!?]+\s+", response)
        if 2 <= len(sentences) <= 10:
            score += 0.2
        elif 1 <= len(sentences) < 2 or 10 < len(sentences) <= 20:
            score += 0.1

        # Check capitalization (proper sentences)
        if response[0].isupper():
            score += 0.1

        return min(1.0, score)

    async def calculate_quality_metrics(
        self,
        query: str,
        response: str,
        context_chunks: list[ContextChunk],
    ) -> QualityMetrics:
        """Calculate comprehensive quality metrics.

        Args:
            query: The original query
            response: The synthesized response
            context_chunks: The context chunks used

        Returns:
            QualityMetrics with all scores
        """
        # Calculate faithfulness
        faithfulness = await self.faithfulness_checker.check_faithfulness(
            response,
            context_chunks,
        )

        # Calculate relevance
        relevance = await self.relevance_filter.check_relevance(query, response)

        # Calculate coherence
        coherence = self._calculate_coherence(response)

        # Detect hallucinations
        (
            _hallucinations,
            hall_count,
        ) = await self.hallucination_detector.detect_hallucinations(
            response,
            context_chunks,
        )

        # Calculate overall confidence
        confidence = (
            self.faithfulness_weight * faithfulness
            + self.relevance_weight * relevance
            + self.coherence_weight * coherence
        )

        # Penalize for hallucinations
        if hall_count > 0:
            penalty = min(0.3 * hall_count, 0.5)
            confidence = max(0.0, confidence - penalty)

        return QualityMetrics(
            faithfulness=faithfulness,
            relevance=relevance,
            coherence=coherence,
            confidence=confidence,
            has_hallucinations=hall_count > 0,
            hallucination_count=hall_count,
        )

    async def calculate_confidence(
        self,
        query: str,
        response: str,
        context_chunks: list[ContextChunk],
    ) -> float:
        """Calculate overall confidence score.

        Args:
            query: The original query
            response: The synthesized response
            context_chunks: The context chunks used

        Returns:
            Confidence score (0-1)
        """
        metrics = await self.calculate_quality_metrics(
            query,
            response,
            context_chunks,
        )
        return metrics.confidence
