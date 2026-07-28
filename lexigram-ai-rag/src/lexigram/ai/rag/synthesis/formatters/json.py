"""JSON formatter.

This module implements a JSON formatter for synthesis results, useful
for API responses and programmatic access.
"""

from __future__ import annotations

from lexigram.ai.rag.synthesis.types import SynthesisResult
from lexigram.serialization import dumps


class JSONFormatter:
    """JSON response formatter.

    This formatter outputs synthesis results as structured JSON with all
    metadata and quality metrics.

    Attributes:
        indent: Indentation for pretty printing (None for compact)
        include_chunks: Whether to include full chunk text
    """

    def __init__(
        self,
        indent: int = 2,
        include_chunks: bool = False,
    ):
        """Initialize the JSON formatter.

        Args:
            indent: JSON indentation (None for compact)
            include_chunks: Include full chunk text in output
        """
        self.indent = indent
        self.include_chunks = include_chunks

    def format(self, result: SynthesisResult) -> str:
        """Format result as JSON.

        Args:
            result: The synthesis result

        Returns:
            JSON string
        """
        # Start with basic result dict
        data = result.to_dict()

        # Add context chunks info
        if self.include_chunks:
            data["context_chunks"] = [
                {
                    "text": chunk.text,
                    "source": chunk.source,
                    "score": chunk.score,
                    "rank": chunk.rank,
                    "metadata": chunk.metadata,
                }
                for chunk in result.context_chunks
            ]
        else:
            data["context_chunks"] = [
                {
                    "source": chunk.source,
                    "score": chunk.score,
                    "rank": chunk.rank,
                    "text_length": len(chunk.text),
                }
                for chunk in result.context_chunks
            ]

        return dumps(data, indent=self.indent, default=str).decode("utf-8")
