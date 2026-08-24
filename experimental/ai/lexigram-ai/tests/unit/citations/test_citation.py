"""Tests for Citation dataclass."""

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.citations.core import Citation


class TestCitation:
    """Tests for Citation dataclass."""

    def test_citation_creation(self):
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
        citation = Citation(
            source_id="src1",
            text_span="This is a test citation text",
            confidence=0.95,
        )

        repr_str = repr(citation)
        assert "src1" in repr_str
        assert "0.95" in repr_str
