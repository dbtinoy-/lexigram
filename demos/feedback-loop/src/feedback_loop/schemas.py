"""Declarative request DTOs for the feedback-loop JSON API.

Annotating a handler parameter with one of these ``DomainModel`` subclasses
tells the framework to deserialize + validate the JSON body before the
handler runs — a malformed payload never reaches demo code; the pipeline
answers with a 422 validation ProblemDetail on its own.
"""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.domain import DomainModel
from lexigram.validation import Field


@dataclass(init=False)
class AskRequest(DomainModel):
    """Body of ``POST /api/ask``."""

    key: str = Field(..., min_length=1, description="Known question key")
    owner: str = Field("web-user", description="Owner tag for the trace")


@dataclass(init=False)
class RateRequest(DomainModel):
    """Body of ``POST /api/rate``."""

    trace_id: str = Field(..., min_length=1, description="Trace id from /api/ask")
    rating: float = Field(..., ge=1, le=5, description="Rating in [1, 5]")
    owner: str = Field("web-user", description="Owner tag for the trace")
    comment: str | None = Field(None, description="Optional free-text comment")


@dataclass(init=False)
class RegressRequest(DomainModel):
    """Body of ``POST /api/regress``."""

    owner: str = Field("web-user", description="Owner whose traces are promoted")


__all__ = ["AskRequest", "RateRequest", "RegressRequest"]
