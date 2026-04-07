"""HyDE (Hypothetical Document Embeddings) package for improved retrieval.

This package provides implementations of HyDE strategies for generating
hypothetical documents to improve retrieval quality.

Reference: "Precise Zero-Shot Dense Retrieval without Relevance Labels"
https://arxiv.org/abs/2212.10496
"""

from __future__ import annotations

from lexigram.ai.rag.hyde.base import AbstractHyDEGenerator
from lexigram.ai.rag.hyde.generators import (
    MultipleHyDEGenerator,
    ReverseHyDEGenerator,
    SingleHyDEGenerator,
    WeightedHyDEGenerator,
)
from lexigram.ai.rag.hyde.protocols import EmbeddingClientProtocol
from lexigram.ai.rag.hyde.types import HyDEResult, HyDEStrategy, HypotheticalDocument
from lexigram.ai.rag.hyde.utils import generate_hyde

__all__ = [
    "AbstractHyDEGenerator",
    "EmbeddingClientProtocol",
    "HyDEResult",
    "HyDEStrategy",
    "HypotheticalDocument",
    "MultipleHyDEGenerator",
    "ReverseHyDEGenerator",
    "SingleHyDEGenerator",
    "WeightedHyDEGenerator",
    "generate_hyde",
]
