"""Type definitions for HyDE (Hypothetical Document Embeddings)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class HyDEStrategy(StrEnum):
    """Strategy for generating hypothetical documents."""

    SINGLE = "single"  # Generate single hypothetical document
    MULTIPLE = "multiple"  # Generate multiple hypothetical documents
    WEIGHTED = "weighted"  # Generate and weight multiple documents
    REVERSE = "reverse"  # Generate query from hypothetical doc


@dataclass
class HypotheticalDocument:
    """A hypothetical document generated for a query."""

    content: str
    query: str
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"HypotheticalDocument(length={len(self.content)}, "
            f"confidence={self.confidence:.2f})"
        )


@dataclass
class HyDEResult:
    """Result of HyDE generation."""

    query: str
    hypothetical_docs: list[HypotheticalDocument]
    strategy: HyDEStrategy
    aggregated_embedding: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
    )

    @property
    def num_documents(self) -> int:
        """Number of hypothetical documents generated."""
        return len(self.hypothetical_docs)

    @property
    def avg_confidence(self) -> float:
        """Average confidence across documents."""
        if not self.hypothetical_docs:
            return 0.0
        return sum(doc.confidence for doc in self.hypothetical_docs) / len(
            self.hypothetical_docs,
        )

    @property
    def total_length(self) -> int:
        """Total length of all hypothetical documents."""
        return sum(len(doc.content) for doc in self.hypothetical_docs)

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"HyDEResult(strategy={self.strategy.value}, "
            f"docs={self.num_documents}, "
            f"avg_conf={self.avg_confidence:.2f})"
        )
