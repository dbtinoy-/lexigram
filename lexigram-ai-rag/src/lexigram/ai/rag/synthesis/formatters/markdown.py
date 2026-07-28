"""Markdown formatter.

This module implements a Markdown formatter for synthesis results with
structured output and citations.
"""

from __future__ import annotations

from lexigram.ai.rag.synthesis.types import SynthesisResult


class MarkdownFormatter:
    """Markdown response formatter.

    This formatter outputs synthesis results as structured Markdown with
    headers, lists, and formatted citations.

    Attributes:
        include_title: Whether to include title header
        include_metadata: Whether to include metadata section
        include_quality: Whether to include quality metrics
        citation_style: Citation style ("numeric" or "footnote")
    """

    def __init__(
        self,
        include_title: bool = True,
        include_metadata: bool = True,
        include_quality: bool = False,
        citation_style: str = "numeric",
    ):
        """Initialize the markdown formatter.

        Args:
            include_title: Include title header
            include_metadata: Include metadata section
            include_quality: Include quality metrics
            citation_style: Citation style
        """
        self.include_title = include_title
        self.include_metadata = include_metadata
        self.include_quality = include_quality
        self.citation_style = citation_style

    def format(self, result: SynthesisResult) -> str:
        """Format result as Markdown.

        Args:
            result: The synthesis result

        Returns:
            Markdown output
        """
        parts = []

        # Add title
        if self.include_title:
            parts.append("# Response\n")

        # Add response text
        parts.append(result.response)
        parts.append("\n")

        # Add sources/citations
        if result.sources or result.citations:
            parts.append("\n## Sources\n")

            if result.citations:
                for citation in result.citations:
                    num = citation.get("number", "?")
                    source = citation.get("source", "Unknown")
                    score = citation.get("score", 0.0)
                    parts.append(f"{num}. {source} (relevance: {score:.2f})\n")
            else:
                for i, source in enumerate(result.sources, 1):
                    parts.append(f"{i}. {source}\n")

        # Add metadata
        if self.include_metadata:
            parts.append("\n## Metadata\n")
            parts.append(f"- **Strategy**: {result.strategy.value}\n")
            parts.append(f"- **Chunks Used**: {result.num_chunks_used}\n")
            parts.append(f"- **Created**: {result.created_at.isoformat()}\n")

        # Add quality metrics
        if self.include_quality and result.quality_metrics:
            metrics = result.quality_metrics
            parts.append("\n## Quality Metrics\n")
            parts.append(f"- **Faithfulness**: {metrics.faithfulness:.2f}\n")
            parts.append(f"- **Relevance**: {metrics.relevance:.2f}\n")
            parts.append(f"- **Coherence**: {metrics.coherence:.2f}\n")
            parts.append(f"- **Confidence**: {metrics.confidence:.2f}\n")

            if metrics.has_hallucinations:
                parts.append(
                    f"- **Hallucinations**: {metrics.hallucination_count} detected\n",
                )

        return "".join(parts)
