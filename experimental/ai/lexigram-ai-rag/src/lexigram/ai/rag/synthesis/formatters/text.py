"""Plain text formatter.

This module implements a simple plain text formatter for synthesis results.
"""

from __future__ import annotations

from lexigram.ai.rag.synthesis.types import SynthesisResult


class PlainTextFormatter:
    """Plain text response formatter.

    This formatter outputs synthesis results as clean plain text without
    any markup or special formatting.

    Attributes:
        include_metadata: Whether to include metadata footer
        include_sources: Whether to include source list
    """

    def __init__(
        self,
        include_metadata: bool = False,
        include_sources: bool = True,
    ):
        """Initialize the plain text formatter.

        Args:
            include_metadata: Include metadata footer
            include_sources: Include source list
        """
        self.include_metadata = include_metadata
        self.include_sources = include_sources

    def format(self, result: SynthesisResult) -> str:
        """Format result as plain text.

        Args:
            result: The synthesis result

        Returns:
            Plain text output
        """
        parts = [result.response]

        # Add sources if requested
        if self.include_sources and result.sources:
            parts.append("\n\nSources:")
            for i, source in enumerate(result.sources, 1):
                parts.append(f"{i}. {source}")

        # Add metadata if requested
        if self.include_metadata:
            parts.append(f"\n\nStrategy: {result.strategy.value}")
            parts.append(f"Chunks used: {result.num_chunks_used}")

            if result.quality_metrics:
                parts.append(
                    f"Confidence: {result.quality_metrics.confidence:.2f}",
                )

        return "".join(parts)
