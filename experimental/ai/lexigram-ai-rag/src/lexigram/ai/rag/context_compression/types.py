"""Types and data structures for context compression."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class CompressionStrategy(StrEnum):
    """Available compression strategies."""

    EXTRACTIVE = "extractive"
    ABSTRACTIVE = "abstractive"
    RERANKING = "reranking"
    TOKEN_LIMIT = "token_limit"  # noqa: S105  # strategy name, not a credential
    SEMANTIC_DEDUP = "semantic_dedup"
    HYBRID = "hybrid"
    LLMLINGUA2 = "llmlingua2"


@dataclass
class CompressionResult:
    """Result of context compression.

    Attributes:
        original_text: Original uncompressed text.
        compressed_text: Compressed text.
        original_tokens: Estimated original token count.
        compressed_tokens: Estimated compressed token count.
        compression_ratio: Ratio of compressed to original size.
        strategy: Strategy used for compression.
        metadata: Additional compression metadata.
    """

    original_text: str
    compressed_text: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    strategy: CompressionStrategy
    metadata: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"CompressionResult(ratio={self.compression_ratio:.2f}, "
            f"tokens={self.original_tokens}→{self.compressed_tokens})"
        )

    @property
    def token_savings(self) -> int:
        """Calculate token savings."""
        return self.original_tokens - self.compressed_tokens

    @property
    def savings_percentage(self) -> float:
        """Calculate savings as percentage."""
        if self.original_tokens == 0:
            return 0.0
        return (self.token_savings / self.original_tokens) * 100
