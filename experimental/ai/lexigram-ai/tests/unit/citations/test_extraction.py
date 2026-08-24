"""Tests for extract_citations_from_chunks."""

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.citations.core import CitationStyle, extract_citations_from_chunks


class TestExtractCitationsFromChunks:
    """Tests for chunk citation extraction."""

    def test_extract_from_chunks(self):
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

        src1 = response.get_source("chunk1")
        assert src1 is not None
        assert src1.title == "ML Guide"
        assert src1.author == "Smith"

    def test_extract_with_default_metadata(self):
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
        assert response.sources[0].id == "source_0"
