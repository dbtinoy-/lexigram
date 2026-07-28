"""Hallucination detector for response quality.

This module implements hallucination detection to identify unsupported
claims in synthesized responses.
"""

from __future__ import annotations

import re

from lexigram.ai.rag.synthesis.types import ContextChunk


class HallucinationChecker:
    """Detect potential hallucinations in responses.

    This component identifies claims in responses that are not supported
    by the context chunks.

    Attributes:
        strict_mode: Whether to use strict detection (lower threshold)
        min_support_ratio: Minimum keyword support ratio
    """

    def __init__(
        self,
        strict_mode: bool = False,
        min_support_ratio: float = 0.4,
    ):
        """Initialize the hallucination detector.

        Args:
            strict_mode: Use strict detection criteria
            min_support_ratio: Minimum support ratio for claims
        """
        self.strict_mode = strict_mode
        self.min_support_ratio = min_support_ratio if not strict_mode else 0.6

    def _extract_claims(self, response: str) -> list[str]:
        """Extract factual claims from response.

        Args:
            response: The response text

        Returns:
            List of claims
        """
        # Split into sentences
        sentences = re.split(r"[.!?]+\s+", response)
        return list(map(str.strip, filter(lambda s: len(s.strip()) > 10, sentences)))

    def _check_claim_support(
        self,
        claim: str,
        context_text: str,
    ) -> tuple[bool, float]:
        """Check if claim is supported by context.

        Args:
            claim: The claim to check
            context_text: The context text

        Returns:
            Tuple of (is_supported, support_ratio)
        """
        # Extract keywords from claim
        claim_words = set(re.findall(r"\b\w{3,}\b", claim.lower()))

        # Remove common words
        stop_words = {
            "the",
            "this",
            "that",
            "these",
            "those",
            "what",
            "which",
            "who",
            "when",
            "where",
            "why",
            "how",
            "can",
            "will",
            "would",
        }
        claim_words -= stop_words

        if not claim_words:
            return True, 1.0

        # Check presence in context
        context_lower = context_text.lower()
        supported_words = sum(1 for word in claim_words if word in context_lower)

        support_ratio = supported_words / len(claim_words)
        is_supported = support_ratio >= self.min_support_ratio

        return is_supported, support_ratio

    async def detect_hallucinations(
        self,
        response: str,
        context_chunks: list[ContextChunk],
    ) -> tuple[list[str], int]:
        """Detect potential hallucinations in response.

        Args:
            response: The synthesized response
            context_chunks: The context chunks used

        Returns:
            Tuple of (list of potential hallucinations, count)
        """
        if not response or not context_chunks:
            return [], 0

        # Combine context
        context_text = " ".join(chunk.text for chunk in context_chunks)

        # Extract claims
        claims = self._extract_claims(response)

        # Check each claim
        hallucinations = []

        for claim in claims:
            is_supported, _support_ratio = self._check_claim_support(
                claim,
                context_text,
            )

            if not is_supported:
                hallucinations.append(claim)

        return hallucinations, len(hallucinations)

    async def has_hallucinations(
        self,
        response: str,
        context_chunks: list[ContextChunk],
    ) -> bool:
        """Check if response has any hallucinations.

        Args:
            response: The synthesized response
            context_chunks: The context chunks used

        Returns:
            True if hallucinations detected
        """
        _, count = await self.detect_hallucinations(response, context_chunks)
        return count > 0
