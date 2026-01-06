"""Citation formatter implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod

from lexigram.ai.rag.citations._models import (
    Citation,
    CitedResponse,
    Source,
    SourceType,
)


class AbstractCitationFormatter(ABC):
    """Base class for citation formatters."""

    @abstractmethod
    def format_citation(
        self,
        citation: Citation,
        source: Source,
        citation_number: int | None = None,
    ) -> str:
        """Format a single citation.

        Args:
            citation: Citation to format
            source: Source being cited
            citation_number: Optional citation number

        Returns:
            Formatted citation string
        """

    @abstractmethod
    def format_bibliography_entry(
        self,
        source: Source,
        number: int | None = None,
    ) -> str:
        """Format a bibliography entry.

        Args:
            source: Source to format
            number: Optional entry number

        Returns:
            Formatted bibliography entry
        """

    def format_response(self, cited_response: CitedResponse) -> str:
        """Format complete response with citations.

        Args:
            cited_response: Response with citations

        Returns:
            Formatted response string with inline citations and bibliography
        """
        # Build text with inline citations
        text = cited_response.text

        # Sort citations by position (if available)
        sorted_citations = sorted(
            cited_response.citations,
            key=lambda c: c.start_char if c.start_char is not None else 0,
            reverse=True,  # Start from end to preserve positions
        )

        # Insert citations
        for citation in sorted_citations:
            source = cited_response.get_source(citation.source_id)
            if (
                source
                and citation.start_char is not None
                and citation.end_char is not None
            ):
                citation_marker = self.format_citation(
                    citation,
                    source,
                    citation.citation_number,
                )
                # Insert after the cited text
                text = (
                    text[: citation.end_char]
                    + citation_marker
                    + text[citation.end_char :]
                )

        # Add bibliography
        bibliography = self.format_bibliography(cited_response.sources)

        return f"{text}\n\n{bibliography}"

    def format_bibliography(self, sources: list[Source]) -> str:
        """Format bibliography from sources.

        Args:
            sources: List of sources

        Returns:
            Formatted bibliography
        """
        if not sources:
            return ""

        entries = []
        for i, source in enumerate(sources, 1):
            entry = self.format_bibliography_entry(source, i)
            entries.append(entry)

        return "References:\n" + "\n".join(entries)


class NumericCitationFormatter(AbstractCitationFormatter):
    """Numeric citation style [1], [2], etc."""

    def format_citation(
        self,
        citation: Citation,
        source: Source,
        citation_number: int | None = None,
    ) -> str:
        """Format as [1], [2], etc."""
        num = citation_number or citation.citation_number or 1
        return f"[{num}]"

    def format_bibliography_entry(
        self,
        source: Source,
        number: int | None = None,
    ) -> str:
        """Format bibliography entry."""
        num = number or 1
        parts = [f"[{num}]"]

        if source.author:
            parts.append(source.author)
        if source.title:
            parts.append(f'"{source.title}"')
        if source.publication_date:
            parts.append(f"({source.publication_date})")
        if source.url:
            parts.append(source.url)

        return " ".join(parts)


class AuthorYearCitationFormatter(AbstractCitationFormatter):
    """Author-year citation style (Smith, 2023)."""

    def format_citation(
        self,
        citation: Citation,
        source: Source,
        citation_number: int | None = None,
    ) -> str:
        """Format as (Author, Year)."""
        author = source.author or "Unknown"
        year = source.publication_date or "n.d."

        # Extract just year if full date provided
        if len(year) > 4:
            year = year[:4]

        return f" ({author}, {year})"

    def format_bibliography_entry(
        self,
        source: Source,
        number: int | None = None,
    ) -> str:
        """Format bibliography entry."""
        author = source.author or "Unknown"
        year = source.publication_date or "n.d."
        if len(year) > 4:
            year = year[:4]

        parts = [f"{author} ({year})."]

        if source.title:
            parts.append(f"{source.title}.")
        if source.url:
            parts.append(f"Retrieved from {source.url}")

        return " ".join(parts)


class FootnoteCitationFormatter(AbstractCitationFormatter):
    """Footnote style with superscript numbers."""

    def format_citation(
        self,
        citation: Citation,
        source: Source,
        citation_number: int | None = None,
    ) -> str:
        """Format as superscript number."""
        num = citation_number or citation.citation_number or 1
        # Using Unicode superscript numbers
        superscripts = "⁰¹²³⁴⁵⁶⁷⁸⁹"
        if num < 10:
            return superscripts[num]
        # For larger numbers, just use regular format
        return f"^{num}"

    def format_bibliography_entry(
        self,
        source: Source,
        number: int | None = None,
    ) -> str:
        """Format as footnote."""
        num = number or 1
        parts = [f"{num}."]

        if source.author:
            parts.append(source.author + ",")
        if source.title:
            parts.append(f'"{source.title},"')
        if source.publication_date:
            parts.append(source.publication_date + ",")
        if source.url:
            parts.append(source.url)

        return " ".join(parts)


class InlineCitationFormatter(AbstractCitationFormatter):
    """Inline source references."""

    def format_citation(
        self,
        citation: Citation,
        source: Source,
        citation_number: int | None = None,
    ) -> str:
        """Format as inline reference."""
        parts = []
        if source.title:
            parts.append(source.title)
        if source.author:
            parts.append(f"by {source.author}")

        if parts:
            return f" (Source: {', '.join(parts)})"
        return f" (Source: {source.id})"

    def format_bibliography_entry(
        self,
        source: Source,
        number: int | None = None,
    ) -> str:
        """Format bibliography entry."""
        parts = []

        if source.author:
            parts.append(source.author)
        if source.title:
            parts.append(f'"{source.title}"')
        if source.publication_date:
            parts.append(f"({source.publication_date})")
        if source.url:
            parts.append(source.url)

        return " - ".join(parts) if parts else source.id


class APACitationFormatter(AbstractCitationFormatter):
    """APA citation style."""

    def format_citation(
        self,
        citation: Citation,
        source: Source,
        citation_number: int | None = None,
    ) -> str:
        """Format as APA in-text citation."""
        author = source.author or "Unknown"
        year = source.publication_date or "n.d."
        if len(year) > 4:
            year = year[:4]

        # Extract last name if full name provided
        if "," in author:
            author = author.split(",")[0]
        elif " " in author:
            author = author.split()[-1]

        return f" ({author}, {year})"

    def format_bibliography_entry(
        self,
        source: Source,
        number: int | None = None,
    ) -> str:
        """Format as APA reference entry."""
        author = source.author or "Unknown"
        year = source.publication_date or "n.d."
        if len(year) > 4:
            year = year[:4]

        parts = [f"{author} ({year})."]

        if source.title:
            parts.append(f"{source.title}.")

        if source.source_type == SourceType.WEB_PAGE and source.url:
            parts.append(f"Retrieved from {source.url}")
        elif source.url:
            parts.append(f"DOI: {source.url}")

        return " ".join(parts)
