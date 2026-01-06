"""Response synthesis package for RAG.

This package provides comprehensive response synthesis capabilities including
multiple synthesis strategies, quality control, context management, and
flexible output formatting.
"""

from __future__ import annotations

# Core types
# Context management
from lexigram.ai.rag.synthesis.context import (
    ContextDeduplicator,
    ContextRanker,
    LengthOptimizer,
)

# Formatters
from lexigram.ai.rag.synthesis.formatters import (
    JSONFormatter,
    MarkdownFormatter,
    PlainTextFormatter,
    ResponseFormatterProtocol,
)

# Quality control
from lexigram.ai.rag.synthesis.quality import (
    ConfidenceScorer,
    FaithfulnessChecker,
    HallucinationChecker,
    RelevanceFilter,
)

# Synthesizers
from lexigram.ai.rag.synthesis.synthesizers import (
    AbstractiveSynthesizer,
    AbstractSynthesizer,
    DirectSynthesizer,
    ExtractiveSynthesizer,
    HybridSynthesizer,
    ResponseSynthesizerProtocol,
)
from lexigram.ai.rag.synthesis.types import (
    ContextChunk,
    OutputFormat,
    QualityMetrics,
    SynthesisConfig,
    SynthesisResult,
    SynthesisStrategy,
)

__all__ = [
    "AbstractSynthesizer",
    "AbstractiveSynthesizer",
    "ConfidenceScorer",
    "ContextChunk",
    "ContextDeduplicator",
    # Context
    "ContextRanker",
    "DirectSynthesizer",
    "ExtractiveSynthesizer",
    # Quality
    "FaithfulnessChecker",
    "HallucinationChecker",
    "HybridSynthesizer",
    "JSONFormatter",
    "LengthOptimizer",
    "MarkdownFormatter",
    "OutputFormat",
    "PlainTextFormatter",
    "QualityMetrics",
    "RelevanceFilter",
    # Formatters
    "ResponseFormatterProtocol",
    # Synthesizers
    "ResponseSynthesizerProtocol",
    "SynthesisConfig",
    "SynthesisResult",
    # Types
    "SynthesisStrategy",
]
