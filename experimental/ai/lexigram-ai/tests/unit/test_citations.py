"""Tests for citation and source tracking."""

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.citations.core import (
    APACitationFormatter,
    AuthorYearCitationFormatter,
    Citation,
    CitationStyle,
    CitationTracker,
    CitedResponse,
    FootnoteCitationFormatter,
    InlineCitationFormatter,
    NumericCitationFormatter,
    Source,
    SourceType,
    extract_citations_from_chunks,
)


# Tests for Source
class TestSource:
    """Tests for Source dataclass."""

    def test_source_creation(self):
        """Test creating a source."""
        source = Source(
            id="src1",
            content="Test content",
            source_type=SourceType.DOCUMENT,
            title="Test Title",
            author="John Doe",
        )

        assert source.id == "src1"
        assert source.content == "Test content"
        assert source.source_type == SourceType.DOCUMENT
        assert source.title == "Test Title"
        assert source.author == "John Doe"

    def test_source_with_metadata(self):
        """Test source with additional metadata."""
        source = Source(
            id="src1",
            content="Content",
            url="https://example.com",
            publication_date="2023",
            page_number=42,
            metadata={"publisher": "ACM"},
        )

        assert source.url == "https://example.com"
        assert source.publication_date == "2023"
        assert source.page_number == 42
        assert source.metadata["publisher"] == "ACM"

    def test_source_repr(self):
        """Test source string representation."""
        source = Source(
            id="src1",
            content="Content",
            title="My Document",
            author="Jane Smith",
        )

        repr_str = repr(source)
        assert "src1" in repr_str
        assert "Jane Smith" in repr_str


# Tests for Citation
class TestCitation:
    """Tests for Citation dataclass."""

    def test_citation_creation(self):
        """Test creating a citation."""
        citation = Citation(
            source_id="src1",
            text_span="Machine learning is...",
            start_char=0,
            end_char=20,
            confidence=0.9,
            relevance_score=0.85,
            citation_number=1,
        )

        assert citation.source_id == "src1"
        assert citation.text_span == "Machine learning is..."
        assert citation.start_char == 0
        assert citation.end_char == 20
        assert citation.confidence == 0.9
        assert citation.relevance_score == 0.85
        assert citation.citation_number == 1

    def test_citation_repr(self):
        """Test citation string representation."""
        citation = Citation(
            source_id="src1",
            text_span="This is a test citation text",
            confidence=0.95,
        )

        repr_str = repr(citation)
        assert "src1" in repr_str
        assert "0.95" in repr_str


# Tests for CitedResponse
class TestCitedResponse:
    """Tests for CitedResponse dataclass."""

    def test_cited_response_creation(self):
        """Test creating cited response."""
        source = Source(id="src1", content="Content")
        citation = Citation(source_id="src1", text_span="text")

        response = CitedResponse(
            text="Response text",
            sources=[source],
            citations=[citation],
            citation_style=CitationStyle.NUMERIC,
        )

        assert response.text == "Response text"
        assert response.num_sources == 1
        assert response.num_citations == 1
        assert response.citation_style == CitationStyle.NUMERIC

    def test_cited_response_properties(self):
        """Test CitedResponse properties."""
        sources = [
            Source(id="src1", content="C1"),
            Source(id="src2", content="C2"),
        ]
        citations = [
            Citation(source_id="src1", text_span="t1", confidence=1.0),
            Citation(source_id="src2", text_span="t2", confidence=0.8),
            Citation(source_id="src1", text_span="t3", confidence=0.9),
        ]

        response = CitedResponse(
            text="Text",
            sources=sources,
            citations=citations,
            citation_style=CitationStyle.NUMERIC,
        )

        assert response.num_sources == 2
        assert response.num_citations == 3
        assert response.avg_confidence == pytest.approx(0.9, abs=0.01)

    def test_get_source(self):
        """Test getting source by ID."""
        source1 = Source(id="src1", content="C1")
        source2 = Source(id="src2", content="C2")

        response = CitedResponse(
            text="Text",
            sources=[source1, source2],
            citations=[],
            citation_style=CitationStyle.NUMERIC,
        )

        found = response.get_source("src2")
        assert found == source2

        not_found = response.get_source("src3")
        assert not_found is None

    def test_get_citations_for_source(self):
        """Test getting citations for specific source."""
        citations = [
            Citation(source_id="src1", text_span="t1"),
            Citation(source_id="src2", text_span="t2"),
            Citation(source_id="src1", text_span="t3"),
        ]

        response = CitedResponse(
            text="Text",
            sources=[],
            citations=citations,
            citation_style=CitationStyle.NUMERIC,
        )

        src1_citations = response.get_citations_for_source("src1")
        assert len(src1_citations) == 2
        assert all(c.source_id == "src1" for c in src1_citations)


# Tests for NumericCitationFormatter
class TestNumericCitationFormatter:
    """Tests for numeric citation formatter."""

    def test_format_citation(self):
        """Test formatting numeric citation."""
        formatter = NumericCitationFormatter()
        source = Source(id="src1", content="Content")
        citation = Citation(source_id="src1", text_span="text", citation_number=5)

        formatted = formatter.format_citation(citation, source, citation_number=5)
        assert formatted == "[5]"

    def test_format_bibliography_entry(self):
        """Test formatting bibliography entry."""
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


# Tests for AuthorYearCitationFormatter
class TestAuthorYearCitationFormatter:
    """Tests for author-year citation formatter."""

    def test_format_citation(self):
        """Test formatting author-year citation."""
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
        """Test with full date (extracts year)."""
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
        """Test formatting bibliography entry."""
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


# Tests for FootnoteCitationFormatter
class TestFootnoteCitationFormatter:
    """Tests for footnote citation formatter."""

    def test_format_citation(self):
        """Test formatting footnote citation."""
        formatter = FootnoteCitationFormatter()
        source = Source(id="src1", content="Content")
        citation = Citation(source_id="src1", text_span="text", citation_number=1)

        formatted = formatter.format_citation(citation, source, citation_number=1)
        # Should be superscript 1
        assert formatted in ["¹", "^1"]

    def test_format_bibliography_entry(self):
        """Test formatting footnote entry."""
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


# Tests for InlineCitationFormatter
class TestInlineCitationFormatter:
    """Tests for inline citation formatter."""

    def test_format_citation_with_title(self):
        """Test formatting inline citation with title."""
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
        """Test formatting inline citation without title."""
        formatter = InlineCitationFormatter()
        source = Source(id="src1", content="Content")
        citation = Citation(source_id="src1", text_span="text")

        formatted = formatter.format_citation(citation, source)
        assert "Source: src1" in formatted


# Tests for APACitationFormatter
class TestAPACitationFormatter:
    """Tests for APA citation formatter."""

    def test_format_citation(self):
        """Test formatting APA citation."""
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
        """Test extracting last name from full name."""
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
        """Test formatting APA reference entry."""
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


# Tests for CitationTracker
class TestCitationTracker:
    """Tests for citation tracker."""

    def test_tracker_creation(self):
        """Test creating citation tracker."""
        tracker = CitationTracker(citation_style=CitationStyle.NUMERIC)
        assert tracker.citation_style == CitationStyle.NUMERIC
        assert len(tracker.sources) == 0
        assert len(tracker.citations) == 0

    def test_add_source(self):
        """Test adding source."""
        tracker = CitationTracker()
        source = Source(id="src1", content="Content")

        tracker.add_source(source)
        assert "src1" in tracker.sources
        assert tracker.sources["src1"] == source

    def test_add_citation(self):
        """Test adding citation."""
        tracker = CitationTracker()
        source = Source(id="src1", content="Content")
        tracker.add_source(source)

        citation = tracker.add_citation(
            source_id="src1",
            text_span="Test text",
            start_char=0,
            end_char=9,
            confidence=0.9,
        )

        assert len(tracker.citations) == 1
        assert citation.source_id == "src1"
        assert citation.citation_number == 1
        assert citation.confidence == 0.9

    def test_add_citation_without_source(self):
        """Test adding citation for non-existent source."""
        tracker = CitationTracker()

        with pytest.raises(ValueError, match="Source .* not found"):
            tracker.add_citation(
                source_id="missing",
                text_span="Text",
            )

    def test_create_cited_response(self):
        """Test creating cited response."""
        tracker = CitationTracker(citation_style=CitationStyle.NUMERIC)

        source = Source(id="src1", content="Content", title="Title")
        tracker.add_source(source)
        tracker.add_citation(source_id="src1", text_span="Text")

        response = tracker.create_cited_response(
            "Response text",
            query="test query",
        )

        assert response.text == "Response text"
        assert response.num_sources == 1
        assert response.num_citations == 1
        assert response.citation_style == CitationStyle.NUMERIC
        assert response.metadata["query"] == "test query"

    def test_multiple_citations(self):
        """Test tracking multiple citations."""
        tracker = CitationTracker()

        source1 = Source(id="src1", content="C1")
        source2 = Source(id="src2", content="C2")

        tracker.add_source(source1)
        tracker.add_source(source2)

        tracker.add_citation(source_id="src1", text_span="T1")
        tracker.add_citation(source_id="src2", text_span="T2")
        tracker.add_citation(source_id="src1", text_span="T3")

        assert len(tracker.citations) == 3
        assert tracker.citations[0].citation_number == 1
        assert tracker.citations[1].citation_number == 2
        assert tracker.citations[2].citation_number == 3

    def test_reset(self):
        """Test resetting tracker."""
        tracker = CitationTracker()

        source = Source(id="src1", content="Content")
        tracker.add_source(source)
        tracker.add_citation(source_id="src1", text_span="Text")

        tracker.reset()

        assert len(tracker.sources) == 0
        assert len(tracker.citations) == 0
        assert tracker._citation_counter == 0


# Tests for extract_citations_from_chunks
class TestExtractCitationsFromChunks:
    """Tests for chunk citation extraction."""

    def test_extract_from_chunks(self):
        """Test extracting citations from chunks."""
        chunks = [
            {
                "id": "chunk1",
                "content": "Machine learning is a subset of AI.",
                "metadata": {
                    "title": "ML Guide",
                    "author": "Smith",
                    "type": "document",
                },
                "score": 0.95,
            },
            {
                "id": "chunk2",
                "content": "Deep learning uses neural networks.",
                "metadata": {
                    "title": "DL Intro",
                    "url": "https://example.com",
                },
                "score": 0.85,
            },
        ]

        response = extract_citations_from_chunks(
            "ML and DL are important.",
            chunks,
            citation_style=CitationStyle.NUMERIC,
        )

        assert response.num_sources == 2
        assert response.num_citations == 2
        assert response.citation_style == CitationStyle.NUMERIC

        # Check sources were created correctly
        src1 = response.get_source("chunk1")
        assert src1 is not None
        assert src1.title == "ML Guide"
        assert src1.author == "Smith"

    def test_extract_with_default_metadata(self):
        """Test extraction with minimal chunk metadata."""
        chunks = [
            {
                "content": "Some content here.",
            },
        ]

        response = extract_citations_from_chunks(
            "Response text",
            chunks,
        )

        assert response.num_sources == 1
        assert response.num_citations == 1
        # Should have auto-generated ID
        assert response.sources[0].id == "source_0"


# Integration tests
class TestIntegration:
    """Integration tests for citation system."""

    def test_full_citation_workflow(self):
        """Test complete citation workflow."""
        # Create tracker
        tracker = CitationTracker(citation_style=CitationStyle.NUMERIC)

        # Add sources
        source1 = Source(
            id="src1",
            content="Machine learning enables computers to learn from data.",
            source_type=SourceType.ARTICLE,
            title="Introduction to ML",
            author="Smith, J.",
            publication_date="2023",
        )

        source2 = Source(
            id="src2",
            content="Neural networks are inspired by the brain.",
            source_type=SourceType.BOOK,
            title="Deep Learning",
            author="Goodfellow, I.",
            publication_date="2016",
        )

        tracker.add_source(source1)
        tracker.add_source(source2)

        # Add citations
        tracker.add_citation(
            source_id="src1",
            text_span="Machine learning",
            confidence=0.95,
        )

        tracker.add_citation(
            source_id="src2",
            text_span="Neural networks",
            confidence=0.90,
        )

        # Create response
        response = tracker.create_cited_response(
            "Machine learning and neural networks are key AI technologies.",
        )

        assert response.num_sources == 2
        assert response.num_citations == 2
        assert response.avg_confidence == pytest.approx(0.925)

    def test_format_with_different_styles(self):
        """Test formatting with different citation styles."""
        tracker = CitationTracker()

        source = Source(
            id="src1",
            content="Content",
            title="Test Document",
            author="Author",
            publication_date="2023",
        )

        tracker.add_source(source)
        citation = tracker.add_citation(source_id="src1", text_span="text")

        # Test different formatters
        styles = [
            CitationStyle.NUMERIC,
            CitationStyle.AUTHOR_YEAR,
            CitationStyle.FOOTNOTE,
            CitationStyle.INLINE,
            CitationStyle.APA,
        ]

        for style in styles:
            response = CitedResponse(
                text="Test",
                sources=[source],
                citations=[citation],
                citation_style=style,
            )

            formatter = tracker._get_formatter(style)
            formatted = formatter.format_citation(citation, source, 1)
            assert formatted  # Should return some formatted string

    def test_bibliography_generation(self):
        """Test generating bibliography."""
        sources = [
            Source(
                id="src1",
                content="C1",
                title="First Source",
                author="Author A",
                publication_date="2023",
            ),
            Source(
                id="src2",
                content="C2",
                title="Second Source",
                author="Author B",
                publication_date="2022",
            ),
        ]

        formatter = NumericCitationFormatter()
        bibliography = formatter.format_bibliography(sources)

        assert "References:" in bibliography
        assert "First Source" in bibliography
        assert "Second Source" in bibliography
        assert "[1]" in bibliography
        assert "[2]" in bibliography
