"""Integration tests for citation system."""

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.citations.core import (
    APACitationFormatter,
    Citation,
    CitationStyle,
    CitationTracker,
    CitedResponse,
    FootnoteCitationFormatter,
    InlineCitationFormatter,
    NumericCitationFormatter,
    Source,
    SourceType,
)


class TestIntegration:
    """Integration tests for citation system."""

    def test_full_citation_workflow(self):
        tracker = CitationTracker(citation_style=CitationStyle.NUMERIC)

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

        response = tracker.create_cited_response(
            "Machine learning and neural networks are key AI technologies.",
        )

        assert response.num_sources == 2
        assert response.num_citations == 2
        assert response.avg_confidence == pytest.approx(0.925)

    def test_format_with_different_styles(self):
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
            assert formatted

    def test_bibliography_generation(self):
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
