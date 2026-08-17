"""Faithfulness checker for response quality.

This module implements faithfulness checking to verify that synthesized
responses are grounded in the provided context.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.contracts.ai import LLMClientProtocol

from lexigram.ai.rag.synthesis.types import ContextChunk


class FaithfulnessChecker:
    """Check if response is faithful to context.

    This component verifies that claims in the response are supported
    by the context chunks.

    Attributes:
        use_llm: Whether to use LLM for verification (more accurate)
        llm_client: Optional LLM client for verification
        threshold: Faithfulness threshold (0-1)
    """

    def __init__(
        self,
        use_llm: bool = False,
        llm_client: LLMClientProtocol | None = None,
        threshold: float = 0.7,
    ):
        """Initialize the faithfulness checker.

        Args:
            use_llm: Whether to use LLM verification
            llm_client: LLM client (required if use_llm=True)
            threshold: Faithfulness threshold
        """
        self.use_llm = use_llm
        self.llm_client = llm_client
        self.threshold = threshold

        if use_llm and not llm_client:
            msg = "LLM client required when use_llm is True"
            raise ValueError(msg)

    def _extract_claims(self, response: str) -> list[str]:
        """Extract factual claims from response.

        Args:
            response: The response text

        Returns:
            List of claim strings
        """
        # Simple sentence splitting as proxy for claims
        sentences = re.split(r"[.!?]+\s+", response)
        return list(map(str.strip, filter(lambda s: len(s.strip()) > 10, sentences)))

    def _check_claim_support(
        self,
        claim: str,
        context_text: str,
    ) -> bool:
        """Check if a claim is supported by context.

        Args:
            claim: The claim to verify
            context_text: The context text

        Returns:
            True if claim appears supported
        """
        # Simple keyword overlap check
        claim_words = set(re.findall(r"\b\w+\b", claim.lower()))
        context_words = set(re.findall(r"\b\w+\b", context_text.lower()))

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
            "is",
            "was",
        }
        claim_words -= stop_words
        context_words -= stop_words

        if not claim_words:
            return True

        # Check overlap ratio
        overlap = len(claim_words & context_words)
        overlap_ratio = overlap / len(claim_words)

        return overlap_ratio >= 0.5

    async def check_faithfulness(
        self,
        response: str,
        context_chunks: list[ContextChunk],
    ) -> float:
        """Check response faithfulness to context.

        Args:
            response: The synthesized response
            context_chunks: The context chunks used

        Returns:
            Faithfulness score (0-1)
        """
        if not response or not context_chunks:
            return 0.0

        # Combine all context
        context_text = " ".join(chunk.text for chunk in context_chunks)

        # Extract claims from response
        claims = self._extract_claims(response)

        if not claims:
            return 1.0  # No claims to verify

        # Check each claim
        supported_claims = 0

        for claim in claims:
            if self._check_claim_support(claim, context_text):
                supported_claims += 1

        # Calculate faithfulness score
        return supported_claims / len(claims)

    async def is_faithful(
        self,
        response: str,
        context_chunks: list[ContextChunk],
    ) -> bool:
        """Check if response meets faithfulness threshold.

        Args:
            response: The synthesized response
            context_chunks: The context chunks used

        Returns:
            True if response is faithful
        """
        score = await self.check_faithfulness(response, context_chunks)
        return score >= self.threshold
