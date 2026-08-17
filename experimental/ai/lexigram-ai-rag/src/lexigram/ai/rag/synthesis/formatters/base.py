"""Base formatter protocol.

This module defines the protocol that all response formatters must implement.
"""

from __future__ import annotations

from typing import Protocol

from lexigram.ai.rag.synthesis.types import SynthesisResult


class ResponseFormatterProtocol(Protocol):
    """Protocol for response formatters.

    All formatter implementations must provide a `format` method that takes
    a synthesis result and returns a formatted string.
    """

    def format(self, result: SynthesisResult) -> str:
        """Format a synthesis result.

        Args:
            result: The synthesis result to format

        Returns:
            Formatted output string
        """
        ...
