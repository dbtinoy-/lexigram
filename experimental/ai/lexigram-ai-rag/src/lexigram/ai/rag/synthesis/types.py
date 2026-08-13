"""Core types for response synthesis.

This module defines the fundamental types used throughout the synthesis system,
including synthesis strategies, results, context chunks, and quality metrics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from lexigram.contracts.ai.chunks import ContextChunk as ContextChunkBase


class SynthesisStrategy(StrEnum):
    """Available synthesis strategies."""

    DIRECT = "direct"  # Simple concatenation
    EXTRACTIVE = "extractive"  # Extract relevant sentences
    ABSTRACTIVE = "abstractive"  # LLM-generated response
    HYBRID = "hybrid"  # Combined extractive + abstractive


class OutputFormat(StrEnum):
    """Available output formats."""

    PLAIN_TEXT = "plain_text"
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"


@dataclass(frozen=True)
class ContextChunk(ContextChunkBase):
    """A chunk of context retrieved for synthesis.

    Attributes:
        text: The chunk text content
        source: Source identifier (document ID, URL, etc.)
        score: Relevance score (0-1)
        metadata: Additional metadata (page number, section, etc.)
        rank: Rank among all retrieved chunks (0-based)
    """

    text: str
    source: str = "unknown"
    score: float | None = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    rank: int = 0

    def __post_init__(self) -> None:
        """Validate chunk data."""
        if not self.text:
            msg = "ContextChunk.text cannot be empty"
            raise ValueError(msg)
        if self.score is not None and (self.score < 0 or self.score > 1):
            msg = "score must be between 0 and 1"
            raise ValueError(msg)


@dataclass
class QualityMetrics:
    """Quality metrics for a synthesized response.

    Attributes:
        faithfulness: How well grounded in context (0-1)
        relevance: How well it answers the query (0-1)
        coherence: How well structured and readable (0-1)
        confidence: Overall confidence in response (0-1)
        has_hallucinations: Whether potential hallucinations detected
        hallucination_count: Number of potential hallucinations
    """

    faithfulness: float = 0.0
    relevance: float = 0.0
    coherence: float = 0.0
    confidence: float = 0.0
    has_hallucinations: bool = False
    hallucination_count: int = 0

    def __post_init__(self) -> None:
        """Validate metrics."""
        for name, value in [
            ("faithfulness", self.faithfulness),
            ("relevance", self.relevance),
            ("coherence", self.coherence),
            ("confidence", self.confidence),
        ]:
            if value < 0 or value > 1:
                msg = f"{name} must be between 0 and 1"
                raise ValueError(msg)

    @property
    def is_high_quality(self) -> bool:
        """Check if response meets high quality thresholds."""
        return (
            self.faithfulness >= 0.7
            and self.relevance >= 0.7
            and self.coherence >= 0.7
            and not self.has_hallucinations
        )

    @property
    def average_score(self) -> float:
        """Calculate average of all metric scores."""
        return (
            self.faithfulness + self.relevance + self.coherence + self.confidence
        ) / 4

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "faithfulness": self.faithfulness,
            "relevance": self.relevance,
            "coherence": self.coherence,
            "confidence": self.confidence,
            "has_hallucinations": self.has_hallucinations,
            "hallucination_count": self.hallucination_count,
            "is_high_quality": self.is_high_quality,
            "average_score": self.average_score,
        }


@dataclass
class SynthesisResult:
    """Result of response synthesis.

    Attributes:
        query: The original query
        response: The synthesized response text
        strategy: Strategy used for synthesis
        context_chunks: Chunks used in synthesis
        quality_metrics: Quality assessment metrics
        sources: List of sources used
        citations: Citation information
        metadata: Additional metadata
        created_at: Timestamp of synthesis
    """

    query: str
    response: str
    strategy: SynthesisStrategy
    context_chunks: list[ContextChunk] = field(default_factory=list)
    quality_metrics: QualityMetrics | None = None
    sources: list[str] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Validate and extract sources."""
        if not self.query:
            msg = "Query cannot be empty"
            raise ValueError(msg)
        if not self.response:
            msg = "Response cannot be empty"
            raise ValueError(msg)

        # Extract unique sources from chunks if not provided
        if not self.sources and self.context_chunks:
            self.sources = list({chunk.source for chunk in self.context_chunks})

    @property
    def num_chunks_used(self) -> int:
        """Number of context chunks used."""
        return len(self.context_chunks)

    @property
    def is_high_confidence(self) -> bool:
        """Check if response has high confidence."""
        if not self.quality_metrics:
            return False
        return self.quality_metrics.confidence >= 0.7

    @property
    def is_faithful(self) -> bool:
        """Check if response is faithful to context."""
        if not self.quality_metrics:
            return False
        return self.quality_metrics.faithfulness >= 0.7

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "response": self.response,
            "strategy": self.strategy.value,
            "num_chunks_used": self.num_chunks_used,
            "sources": self.sources,
            "citations": self.citations,
            "quality_metrics": (
                self.quality_metrics.to_dict() if self.quality_metrics else None
            ),
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class SynthesisConfig:
    """Configuration for response synthesis.

    Attributes:
        strategy: Synthesis strategy to use
        max_context_length: Maximum context length in tokens
        max_response_length: Maximum response length in tokens
        include_citations: Whether to include citations
        output_format: Desired output format
        quality_check: Whether to run quality checks
        min_confidence: Minimum confidence threshold
        metadata: Additional configuration metadata
    """

    enabled: bool = True
    strategy: SynthesisStrategy = SynthesisStrategy.HYBRID
    model: str | None = None
    max_context_length: int = 4000
    max_response_length: int = 500
    include_citations: bool = True
    output_format: OutputFormat = OutputFormat.MARKDOWN
    quality_check: bool = True
    min_confidence: float = 0.5
    error_strategy: str = "graceful"
    fallback_strategy: SynthesisStrategy = SynthesisStrategy.DIRECT
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.max_context_length <= 0:
            msg = "max_context_length must be positive"
            raise ValueError(msg)
        if self.max_response_length <= 0:
            msg = "max_response_length must be positive"
            raise ValueError(msg)
        if self.min_confidence < 0 or self.min_confidence > 1:
            msg = "min_confidence must be between 0 and 1"
            raise ValueError(msg)
