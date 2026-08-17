"""Citation domain models and enums."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class CitationStyle(StrEnum):
    """Citation formatting styles."""

    NUMERIC = "numeric"  # [1], [2], etc.
    AUTHOR_YEAR = "author_year"  # (Smith, 2023)
    FOOTNOTE = "footnote"  # Superscript numbers
    INLINE = "inline"  # Inline source references
    APA = "apa"  # APA style
    MLA = "mla"  # MLA style
    CHICAGO = "chicago"  # Chicago style
    CUSTOM = "custom"  # Custom format


class SourceType(StrEnum):
    """Types of sources."""

    DOCUMENT = "document"
    WEB_PAGE = "web_page"
    ARTICLE = "article"
    BOOK = "book"
    PAPER = "paper"
    DATABASE = "database"
    API = "api"
    INTERNAL = "internal"
    UNKNOWN = "unknown"


@dataclass
class Source:
    """A source of information."""

    id: str
    content: str
    source_type: SourceType = SourceType.UNKNOWN
    title: str | None = None
    author: str | None = None
    url: str | None = None
    publication_date: str | None = None
    page_number: int | None = None
    chapter: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        parts = [f"id={self.id}"]
        if self.title:
            parts.append(f"title={self.title[:30]}")
        if self.author:
            parts.append(f"author={self.author}")
        return f"Source({', '.join(parts)})"


@dataclass
class Citation:
    """A citation linking text to source."""

    source_id: str
    text_span: str
    start_char: int | None = None
    end_char: int | None = None
    confidence: float = 1.0
    relevance_score: float = 1.0
    citation_number: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"Citation(source={self.source_id}, "
            f"span='{self.text_span[:30]}...', "
            f"conf={self.confidence:.2f})"
        )


@dataclass
class CitedResponse:
    """A response with citations."""

    text: str
    sources: list[Source]
    citations: list[Citation]
    citation_style: CitationStyle = CitationStyle.NUMERIC
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
    )

    @property
    def num_sources(self) -> int:
        """Number of unique sources."""
        return len(self.sources)

    @property
    def num_citations(self) -> int:
        """Number of citations."""
        return len(self.citations)

    @property
    def avg_confidence(self) -> float:
        """Average citation confidence."""
        if not self.citations:
            return 0.0
        return sum(c.confidence for c in self.citations) / len(self.citations)

    def get_source(self, source_id: str) -> Source | None:
        """Get source by ID."""
        for source in self.sources:
            if source.id == source_id:
                return source
        return None

    def get_citations_for_source(self, source_id: str) -> list[Citation]:
        """Get all citations for a source."""
        return list(filter(lambda c: c.source_id == source_id, self.citations))

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"CitedResponse(sources={self.num_sources}, "
            f"citations={self.num_citations}, "
            f"style={self.citation_style.value})"
        )
