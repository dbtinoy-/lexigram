"""Tests for CitedResponse dataclass."""

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.citations.core import Citation, CitationStyle, CitedResponse, Source


class TestCitedResponse:
    """Tests for CitedResponse dataclass."""

    def test_cited_response_creation(self):
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
