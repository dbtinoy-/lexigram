"""Citation tracker and extraction helpers."""

from __future__ import annotations

from typing import Any

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


class CitationTracker:
    """Tracks citations throughout RAG pipeline."""

    def __init__(self, citation_style: CitationStyle = CitationStyle.NUMERIC):
        """Initialize citation tracker.

        Args:
            citation_style: Default citation style
        """
        self.citation_style = citation_style
        self.sources: dict[str, Source] = {}
        self.citations: list[Citation] = []
        self._citation_counter = 0

    def add_source(self, source: Source) -> None:
        """Add a source to tracking.

        Args:
            source: Source to add
        """
        self.sources[source.id] = source

    def add_citation(
        self,
        source_id: str,
        text_span: str,
        start_char: int | None = None,
        end_char: int | None = None,
        confidence: float = 1.0,
        relevance_score: float = 1.0,
    ) -> Citation:
        """Add a citation.

        Args:
            source_id: ID of source being cited
            text_span: Text being cited
            start_char: Start character position
            end_char: End character position
            confidence: Citation confidence
            relevance_score: Relevance score

        Returns:
            Created citation

        Raises:
            ValueError: If source not found
        """
        if source_id not in self.sources:
            msg = f"Source {source_id} not found. Add source first."
            raise ValueError(msg)

        self._citation_counter += 1

        citation = Citation(
            source_id=source_id,
            text_span=text_span,
            start_char=start_char,
            end_char=end_char,
            confidence=confidence,
            relevance_score=relevance_score,
            citation_number=self._citation_counter,
        )

        self.citations.append(citation)
        return citation

    def create_cited_response(self, text: str, **metadata: Any) -> CitedResponse:
        """Create cited response from tracked data.

        Args:
            text: Response text
            **metadata: Additional metadata

        Returns:
            CitedResponse with all tracked sources and citations
        """
        return CitedResponse(
            text=text,
            sources=list(self.sources.values()),
            citations=self.citations,
            citation_style=self.citation_style,
            metadata=metadata,
        )

    def format_response(self, cited_response: CitedResponse) -> str:
        """Format response with citations.

        Args:
            cited_response: Response to format

        Returns:
            Formatted response with inline citations and bibliography
        """
        formatter = self._get_formatter(cited_response.citation_style)
        return formatter.format_response(cited_response)

    def _get_formatter(self, style: CitationStyle) -> AbstractCitationFormatter:
        """Get formatter for citation style.

        Args:
            style: Citation style

        Returns:
            Appropriate formatter

        Raises:
            ValueError: If style not supported
        """
        formatters = {
            CitationStyle.NUMERIC: NumericCitationFormatter(),
            CitationStyle.AUTHOR_YEAR: AuthorYearCitationFormatter(),
            CitationStyle.FOOTNOTE: FootnoteCitationFormatter(),
            CitationStyle.INLINE: InlineCitationFormatter(),
            CitationStyle.APA: APACitationFormatter(),
        }

        formatter = formatters.get(style)
        if not formatter:
            msg = f"Citation style {style} not yet supported"
            raise ValueError(msg)

        return formatter

    def reset(self) -> None:
        """Reset tracker state."""
        self.sources.clear()
        self.citations.clear()
        self._citation_counter = 0


def extract_citations_from_chunks(
    response_text: str,
    retrieved_chunks: list[dict[str, Any]],
    citation_style: CitationStyle = CitationStyle.NUMERIC,
) -> CitedResponse:
    """Extract citations from retrieved chunks.

    Args:
        response_text: Generated response text
        retrieved_chunks: List of retrieved chunks with metadata
        citation_style: Citation style to use

    Returns:
        CitedResponse with citations from chunks
    """
    tracker = CitationTracker(citation_style=citation_style)

    # Add sources from chunks
    for i, chunk in enumerate(retrieved_chunks):
        source_id = chunk.get("id", f"source_{i}")
        content = chunk.get("content", "")
        metadata = chunk.get("metadata", {})

        source = Source(
            id=source_id,
            content=content,
            source_type=SourceType(metadata.get("type", "document")),
            title=metadata.get("title"),
            author=metadata.get("author"),
            url=metadata.get("url"),
            publication_date=metadata.get("date"),
            page_number=metadata.get("page"),
            metadata=metadata,
        )

        tracker.add_source(source)

        # Simple citation extraction: assume each chunk contributed to response
        # In production, would use more sophisticated attribution
        relevance_score = chunk.get("score", 1.0)

        tracker.add_citation(
            source_id=source_id,
            text_span=content[:100],  # First 100 chars as representative span
            confidence=0.8,  # Default confidence
            relevance_score=relevance_score,
        )

    return tracker.create_cited_response(response_text)
