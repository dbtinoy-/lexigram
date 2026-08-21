"""Exception hierarchy for the docs ask demo."""

from __future__ import annotations

from lexigram.contracts.ai.exceptions import RAGError


class DocsAskError(RAGError):
    """Base error for rag-docs domain operations."""


class NoResultsError(DocsAskError):
    """Raised when the corpus is empty or nothing matches the query."""


class UnknownStrategyError(DocsAskError):
    """Raised when a retrieval strategy name is not registered."""


class SynthesisFailedError(DocsAskError):
    """Raised when answer synthesis fails."""


__all__ = [
    "DocsAskError",
    "NoResultsError",
    "SynthesisFailedError",
    "UnknownStrategyError",
]
