"""Tests for CitationTracker."""

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.citations.core import Citation, CitationStyle, CitationTracker, Source


class TestCitationTracker:
    """Tests for citation tracker."""

    def test_tracker_creation(self):
        tracker = CitationTracker(citation_style=CitationStyle.NUMERIC)
        assert tracker.citation_style == CitationStyle.NUMERIC
        assert len(tracker.sources) == 0
        assert len(tracker.citations) == 0

    def test_add_source(self):
        tracker = CitationTracker()
        source = Source(id="src1", content="Content")

        tracker.add_source(source)
        assert "src1" in tracker.sources
        assert tracker.sources["src1"] == source

    def test_add_citation(self):
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
        tracker = CitationTracker()

        with pytest.raises(ValueError, match="Source .* not found"):
            tracker.add_citation(
                source_id="missing",
                text_span="Text",
            )

    def test_create_cited_response(self):
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
        tracker = CitationTracker()

        source = Source(id="src1", content="Content")
        tracker.add_source(source)
        tracker.add_citation(source_id="src1", text_span="Text")

        tracker.reset()

        assert len(tracker.sources) == 0
        assert len(tracker.citations) == 0
        assert tracker._citation_counter == 0
