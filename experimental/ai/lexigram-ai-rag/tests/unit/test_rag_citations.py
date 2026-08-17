"""Unit tests for lexigram.ai.rag.citations.core module."""

from __future__ import annotations

import pytest

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


# ── Data classes ─────────────────────────────────────────────────────

class TestSource:
    def test_defaults(self) -> None:
        s = Source(id="s1", content="hello")
        assert s.source_type == SourceType.UNKNOWN
        assert s.title is None
        assert s.metadata == {}
        assert s.timestamp  # auto-generated

    def test_repr_simple(self) -> None:
        s = Source(id="s1", content="hello")
        assert "id=s1" in repr(s)

    def test_repr_with_title_author(self) -> None:
        s = Source(id="s1", content="x", title="My Title", author="Bob")
        r = repr(s)
        assert "title=My Title" in r
        assert "author=Bob" in r


class TestCitation:
    def test_defaults(self) -> None:
        c = Citation(source_id="s1", text_span="hello world")
        assert c.confidence == 1.0
        assert c.citation_number is None
        assert c.metadata == {}

    def test_repr(self) -> None:
        c = Citation(source_id="s1", text_span="short text")
        r = repr(c)
        assert "source=s1" in r
        assert "conf=1.00" in r


class TestCitedResponse:
    def test_properties(self) -> None:
        src = Source(id="s1", content="data")
        cit = Citation(source_id="s1", text_span="data", confidence=0.8)
        resp = CitedResponse(text="answer", sources=[src], citations=[cit])
        assert resp.num_sources == 1
        assert resp.num_citations == 1
        assert resp.avg_confidence == 0.8

    def test_avg_confidence_empty(self) -> None:
        resp = CitedResponse(text="answer", sources=[], citations=[])
        assert resp.avg_confidence == 0.0

    def test_get_source(self) -> None:
        src = Source(id="s1", content="data")
        resp = CitedResponse(text="a", sources=[src], citations=[])
        assert resp.get_source("s1") is src
        assert resp.get_source("nope") is None

    def test_get_citations_for_source(self) -> None:
        cit1 = Citation(source_id="s1", text_span="a")
        cit2 = Citation(source_id="s2", text_span="b")
        cit3 = Citation(source_id="s1", text_span="c")
        resp = CitedResponse(text="x", sources=[], citations=[cit1, cit2, cit3])
        assert len(resp.get_citations_for_source("s1")) == 2
        assert len(resp.get_citations_for_source("s2")) == 1

    def test_repr(self) -> None:
        resp = CitedResponse(
            text="x", sources=[], citations=[],
            citation_style=CitationStyle.NUMERIC,
        )
        assert "CitedResponse" in repr(resp)


# ── Formatters ───────────────────────────────────────────────────────

class TestNumericFormatter:
    def test_format_citation(self) -> None:
        fmt = NumericCitationFormatter()
        src = Source(id="s1", content="x")
        cit = Citation(source_id="s1", text_span="x")
        assert fmt.format_citation(cit, src, citation_number=3) == "[3]"

    def test_format_bibliography_entry_full(self) -> None:
        fmt = NumericCitationFormatter()
        src = Source(
            id="s1", content="x", author="Smith",
            title="AI Paper", publication_date="2024", url="http://ex.com",
        )
        entry = fmt.format_bibliography_entry(src, number=1)
        assert "[1]" in entry
        assert "Smith" in entry
        assert '"AI Paper"' in entry
        assert "(2024)" in entry
        assert "http://ex.com" in entry


class TestAuthorYearFormatter:
    def test_format_citation(self) -> None:
        fmt = AuthorYearCitationFormatter()
        src = Source(id="s1", content="x", author="Smith", publication_date="2024-01-01")
        cit = Citation(source_id="s1", text_span="x")
        result = fmt.format_citation(cit, src)
        assert "(Smith, 2024)" in result

    def test_format_citation_no_author(self) -> None:
        fmt = AuthorYearCitationFormatter()
        src = Source(id="s1", content="x")
        cit = Citation(source_id="s1", text_span="x")
        result = fmt.format_citation(cit, src)
        assert "Unknown" in result

    def test_format_bibliography_entry(self) -> None:
        fmt = AuthorYearCitationFormatter()
        src = Source(id="s1", content="x", author="Doe", title="My Title", url="http://a.com")
        entry = fmt.format_bibliography_entry(src, number=1)
        assert "Doe" in entry
        assert "My Title" in entry


class TestFootnoteFormatter:
    def test_format_citation_small(self) -> None:
        fmt = FootnoteCitationFormatter()
        src = Source(id="s1", content="x")
        cit = Citation(source_id="s1", text_span="x", citation_number=3)
        result = fmt.format_citation(cit, src)
        assert result == "³"

    def test_format_citation_large(self) -> None:
        fmt = FootnoteCitationFormatter()
        src = Source(id="s1", content="x")
        cit = Citation(source_id="s1", text_span="x", citation_number=15)
        result = fmt.format_citation(cit, src)
        assert "^15" in result

    def test_format_bibliography_entry(self) -> None:
        fmt = FootnoteCitationFormatter()
        src = Source(id="s1", content="x", author="A", title="T", publication_date="2024")
        entry = fmt.format_bibliography_entry(src, number=2)
        assert "2." in entry
        assert "A" in entry


class TestInlineFormatter:
    def test_format_citation_with_title(self) -> None:
        fmt = InlineCitationFormatter()
        src = Source(id="s1", content="x", title="My Doc", author="Alice")
        cit = Citation(source_id="s1", text_span="x")
        result = fmt.format_citation(cit, src)
        assert "My Doc" in result
        assert "Alice" in result

    def test_format_citation_no_title(self) -> None:
        fmt = InlineCitationFormatter()
        src = Source(id="s1", content="x")
        cit = Citation(source_id="s1", text_span="x")
        result = fmt.format_citation(cit, src)
        assert "s1" in result

    def test_format_bibliography_entry_no_metadata(self) -> None:
        fmt = InlineCitationFormatter()
        src = Source(id="s1", content="x")
        entry = fmt.format_bibliography_entry(src)
        assert entry == "s1"


class TestAPAFormatter:
    def test_format_citation_last_name(self) -> None:
        fmt = APACitationFormatter()
        src = Source(id="s1", content="x", author="John Smith", publication_date="2024")
        cit = Citation(source_id="s1", text_span="x")
        result = fmt.format_citation(cit, src)
        assert "(Smith, 2024)" in result

    def test_format_bibliography_web(self) -> None:
        fmt = APACitationFormatter()
        src = Source(
            id="s1", content="x", author="A",
            source_type=SourceType.WEB_PAGE, url="http://a.com",
        )
        entry = fmt.format_bibliography_entry(src)
        assert "Retrieved from" in entry


# ── CitationTracker ──────────────────────────────────────────────────

class TestCitationTracker:
    def test_add_source_and_citation(self) -> None:
        tracker = CitationTracker()
        src = Source(id="s1", content="data")
        tracker.add_source(src)
        cit = tracker.add_citation("s1", "data", confidence=0.9)
        assert cit.citation_number == 1
        assert cit.confidence == 0.9

    def test_add_citation_unknown_source_raises(self) -> None:
        tracker = CitationTracker()
        with pytest.raises(ValueError, match="not found"):
            tracker.add_citation("nope", "text")

    def test_create_cited_response(self) -> None:
        tracker = CitationTracker(CitationStyle.INLINE)
        tracker.add_source(Source(id="s1", content="data"))
        tracker.add_citation("s1", "data")
        resp = tracker.create_cited_response("answer", quality="high")
        assert resp.text == "answer"
        assert resp.citation_style == CitationStyle.INLINE
        assert resp.metadata["quality"] == "high"

    def test_format_response(self) -> None:
        tracker = CitationTracker(CitationStyle.NUMERIC)
        tracker.add_source(Source(id="s1", content="d", title="T"))
        tracker.add_citation("s1", "d", start_char=0, end_char=1)
        resp = tracker.create_cited_response("answer")
        formatted = tracker.format_response(resp)
        assert "References:" in formatted

    def test_unsupported_style_raises(self) -> None:
        tracker = CitationTracker()
        with pytest.raises(ValueError, match="not yet supported"):
            tracker._get_formatter(CitationStyle.CUSTOM)

    def test_reset(self) -> None:
        tracker = CitationTracker()
        tracker.add_source(Source(id="s1", content="x"))
        tracker.add_citation("s1", "x")
        tracker.reset()
        assert len(tracker.sources) == 0
        assert len(tracker.citations) == 0

    def test_format_bibliography_empty(self) -> None:
        fmt = NumericCitationFormatter()
        assert fmt.format_bibliography([]) == ""


# ── extract_citations_from_chunks ────────────────────────────────────

class TestExtractCitations:
    def test_basic_extraction(self) -> None:
        chunks = [
            {"id": "c1", "content": "Hello world", "score": 0.9, "metadata": {"title": "Doc1"}},
            {"id": "c2", "content": "Foo bar", "score": 0.7, "metadata": {}},
        ]
        resp = extract_citations_from_chunks("Generated answer", chunks)
        assert resp.num_sources == 2
        assert resp.num_citations == 2
        assert resp.citation_style == CitationStyle.NUMERIC

    def test_extraction_with_custom_style(self) -> None:
        chunks = [{"content": "data", "metadata": {}}]
        resp = extract_citations_from_chunks("answer", chunks, CitationStyle.APA)
        assert resp.citation_style == CitationStyle.APA

    def test_extraction_auto_id(self) -> None:
        chunks = [{"content": "data", "metadata": {}}]
        resp = extract_citations_from_chunks("x", chunks)
        assert resp.sources[0].id == "source_0"
