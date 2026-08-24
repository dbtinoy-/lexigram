"""Tests for citation formatters."""

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.citations.core import (
    APACitationFormatter,
    AuthorYearCitationFormatter,
    Citation,
    CitationStyle,
    FootnoteCitationFormatter,
    InlineCitationFormatter,
    NumericCitationFormatter,
    Source,
    SourceType,
)


class TestNumericCitationFormatter:
    """Tests for numeric citation formatter."""

    def test_format_citation(self):
        formatter = NumericCitationFormatter()
        source = Source(id="src1", content="Content")
        citation = Citation(source_id="src1", text_span="text", citation_number=5)

        formatted = formatter.format_citation(citation, source, citation_number=5)
        assert formatted == "[5]"

    def test_format_bibliography_entry(self):
        formatter = NumericCitationFormatter()
        source = Source(
            id="src1",
            content="Content",
            title="Machine Learning Basics",
            author="John Doe",
            publication_date="2023",
            url="https://example.com",
        )

        entry = formatter.format_bibliography_entry(source, number=1)
        assert "[1]" in entry
        assert "John Doe" in entry
        assert "Machine Learning Basics" in entry
        assert "2023" in entry
        assert "https://example.com" in entry


class TestAuthorYearCitationFormatter:
    """Tests for author-year citation formatter."""

    def test_format_citation(self):
        formatter = AuthorYearCitationFormatter()
        source = Source(
            id="src1",
            content="Content",
            author="Smith",
            publication_date="2023",
        )
        citation = Citation(source_id="src1", text_span="text")

        formatted = formatter.format_citation(citation, source)
        assert "(Smith, 2023)" in formatted

    def test_format_citation_full_date(self):
        formatter = AuthorYearCitationFormatter()
        source = Source(
            id="src1",
            content="Content",
            author="Jones",
            publication_date="2023-05-15",
        )
        citation = Citation(source_id="src1", text_span="text")

        formatted = formatter.format_citation(citation, source)
        assert "(Jones, 2023)" in formatted

    def test_format_bibliography_entry(self):
        formatter = AuthorYearCitationFormatter()
        source = Source(
            id="src1",
            content="Content",
            title="AI Research",
            author="Smith",
            publication_date="2023",
            url="https://example.com",
        )

        entry = formatter.format_bibliography_entry(source)
        assert "Smith (2023)" in entry
        assert "AI Research" in entry


class TestFootnoteCitationFormatter:
    """Tests for footnote citation formatter."""

    def test_format_citation(self):
        formatter = FootnoteCitationFormatter()
        source = Source(id="src1", content="Content")
        citation = Citation(source_id="src1", text_span="text", citation_number=1)

        formatted = formatter.format_citation(citation, source, citation_number=1)
        assert formatted in ["¹", "^1"]

    def test_format_bibliography_entry(self):
        formatter = FootnoteCitationFormatter()
        source = Source(
            id="src1",
            content="Content",
            title="Test Title",
            author="Author",
            publication_date="2023",
        )

        entry = formatter.format_bibliography_entry(source, number=1)
        assert "1." in entry
        assert "Author" in entry
        assert "Test Title" in entry


class TestInlineCitationFormatter:
    """Tests for inline citation formatter."""

    def test_format_citation_with_title(self):
        formatter = InlineCitationFormatter()
        source = Source(
            id="src1",
            content="Content",
            title="Document Title",
            author="Author Name",
        )
        citation = Citation(source_id="src1", text_span="text")

        formatted = formatter.format_citation(citation, source)
        assert "Source:" in formatted
        assert "Document Title" in formatted

    def test_format_citation_without_title(self):
        formatter = InlineCitationFormatter()
        source = Source(id="src1", content="Content")
        citation = Citation(source_id="src1", text_span="text")

        formatted = formatter.format_citation(citation, source)
        assert "Source: src1" in formatted


class TestAPACitationFormatter:
    """Tests for APA citation formatter."""

    def test_format_citation(self):
        formatter = APACitationFormatter()
        source = Source(
            id="src1",
            content="Content",
            author="Smith, J.",
            publication_date="2023",
        )
        citation = Citation(source_id="src1", text_span="text")

        formatted = formatter.format_citation(citation, source)
        assert "(Smith, 2023)" in formatted

    def test_format_citation_last_name_extraction(self):
        formatter = APACitationFormatter()
        source = Source(
            id="src1",
            content="Content",
            author="John Smith",
            publication_date="2023",
        )
        citation = Citation(source_id="src1", text_span="text")

        formatted = formatter.format_citation(citation, source)
        assert "(Smith, 2023)" in formatted

    def test_format_bibliography_entry(self):
        formatter = APACitationFormatter()
        source = Source(
            id="src1",
            content="Content",
            title="Machine Learning",
            author="Smith, J.",
            publication_date="2023",
            source_type=SourceType.WEB_PAGE,
            url="https://example.com",
        )

        entry = formatter.format_bibliography_entry(source)
        assert "Smith, J. (2023)" in entry
        assert "Machine Learning" in entry
        assert "Retrieved from" in entry
