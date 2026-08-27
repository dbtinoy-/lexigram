"""Exception hierarchy for the rag-docs demo — the **error taxonomy** lesson.

Every domain error extends ``DocsAskError(RAGError)`` from the contracts
layer.  The controller maps these to HTTP status codes via
``ResultResponseMapper.register(...)``:

- ``UnknownStrategyError``  → 400 Bad Request
- ``NoResultsError``        → 404 Not Found
- ``SynthesisFailedError``  → 502 Bad Gateway

Handlers return ``Result[dict, DocsAskError]`` — the web pipeline does
the boring work of mapping error types to ProblemDetail responses.

Usage::

    return Err(UnknownStrategyError(f"unknown strategy {strategy!r}"))

...instead of raising exceptions and catching them in every handler.
"""

from __future__ import annotations

from lexigram.contracts.ai.exceptions import RAGError


class DocsAskError(RAGError):
    """Base error for rag-docs domain operations.

    All domain-specific errors inherit from this so the controller can
    catch the entire subtree with a single ``except DocsAskError`` if
    needed (though Result patterns make that rare).
    """


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
