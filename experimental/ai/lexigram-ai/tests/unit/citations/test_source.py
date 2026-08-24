"""Tests for Source dataclass."""

import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

from lexigram.ai.rag.citations.core import Source, SourceType


class TestSource:
    """Tests for Source dataclass."""

    def test_source_creation(self):
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
        source = Source(
            id="src1",
            content="Content",
            title="My Document",
            author="Jane Smith",
        )

        repr_str = repr(source)
        assert "src1" in repr_str
        assert "Jane Smith" in repr_str
