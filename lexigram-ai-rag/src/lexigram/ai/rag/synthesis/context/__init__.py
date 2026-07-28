"""Context management components for synthesis.

This package provides components for managing context before synthesis,
including ranking, deduplication, and length optimization.
"""

from __future__ import annotations

from lexigram.ai.rag.synthesis.context.deduplicator import ContextDeduplicator
from lexigram.ai.rag.synthesis.context.optimizer import LengthOptimizer
from lexigram.ai.rag.synthesis.context.ranker import ContextRanker

__all__ = [
    "ContextDeduplicator",
    "ContextRanker",
    "LengthOptimizer",
]
