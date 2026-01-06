"""Citation and source tracking for RAG systems."""

from __future__ import annotations

from lexigram.ai.rag.citations._formatters import (
    AbstractCitationFormatter,
    APACitationFormatter,
    AuthorYearCitationFormatter,
    FootnoteCitationFormatter,
    InlineCitationFormatter,
    NumericCitationFormatter,
)
from lexigram.ai.rag.citations._models import (
    Citation,
    CitationStyle,
    CitedResponse,
    Source,
    SourceType,
)
from lexigram.ai.rag.citations._tracker import (
    CitationTracker,
    extract_citations_from_chunks,
)

__all__ = [
    "APACitationFormatter",
    "AbstractCitationFormatter",
    "AuthorYearCitationFormatter",
    "Citation",
    "CitationStyle",
    "CitationTracker",
    "CitedResponse",
    "FootnoteCitationFormatter",
    "InlineCitationFormatter",
    "NumericCitationFormatter",
    "Source",
    "SourceType",
    "extract_citations_from_chunks",
]
