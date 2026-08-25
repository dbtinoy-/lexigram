"""Tests for the Chunk dataclass and basic chunkers (fixed-size, recursive)."""

from __future__ import annotations

import pytest

from lexigram.ai.rag.chunking import Chunk, FixedSizeChunker, RecursiveChunker


class TestChunk:
    """Test Chunk dataclass."""

    def test_chunk_creation(self):
        """Test creating a chunk."""
        chunk = Chunk(
            text="Hello world",
            start_index=0,
            end_index=11,
            chunk_index=0,
        )

        assert chunk.text == "Hello world"
        assert chunk.start_index == 0
        assert chunk.end_index == 11
        assert chunk.chunk_index == 0
        assert chunk.metadata == {}

    def test_chunk_with_metadata(self):
        """Test chunk with metadata."""
        metadata = {"source": "test.txt", "page": 1}
        chunk = Chunk(
            text="Hello",
            start_index=0,
            end_index=5,
            chunk_index=0,
            metadata=metadata,
        )

        assert chunk.metadata == metadata

    def test_chunk_length(self):
        """Test chunk length."""
        chunk = Chunk(text="Hello", start_index=0, end_index=5, chunk_index=0)
        assert len(chunk) == 5


class TestFixedSizeChunker:
    """Test fixed-size chunking."""

    def test_basic_chunking(self, chunking_sample_text):
        """Test basic fixed-size chunking."""
        chunker = FixedSizeChunker(chunk_size=50, overlap=10)
        chunks = chunker.chunk(chunking_sample_text)

        assert len(chunks) > 0
        assert all(isinstance(c, Chunk) for c in chunks)
        # Check indexes are sequential
        assert all(chunks[i].chunk_index == i for i in range(len(chunks)))

    def test_chunk_sizes(self):
        """Test that chunks respect size limits."""
        text = "word " * 200  # 1000 characters
        chunker = FixedSizeChunker(chunk_size=100, overlap=0)
        chunks = chunker.chunk(text)

        for chunk in chunks[:-1]:  # All but last
            assert len(chunk.text) <= 110  # Some tolerance for word boundaries

    def test_overlap(self):
        """Test overlap between chunks."""
        text = "word " * 100
        chunker = FixedSizeChunker(chunk_size=50, overlap=10)
        chunks = chunker.chunk(text)

        if len(chunks) > 1:
            # Check that there's some overlap
            assert chunks[1].start_index < chunks[0].end_index

    def test_empty_text(self):
        """Test handling of empty text."""
        chunker = FixedSizeChunker()
        chunks = chunker.chunk("")

        assert len(chunks) == 0

    def test_separator_handling(self):
        """Test separator preservation."""
        text = "word1 word2 word3 word4 word5"
        chunker_keep = FixedSizeChunker(chunk_size=15, overlap=0, keep_separator=True)
        chunker_remove = FixedSizeChunker(
            chunk_size=15, overlap=0, keep_separator=False,
        )

        chunks_keep = chunker_keep.chunk(text)
        chunks_remove = chunker_remove.chunk(text)

        # With keep_separator, chunks should include spaces
        assert " " in chunks_keep[0].text
        # Without keep_separator, might not (depending on split point)

    def test_invalid_config(self):
        """Test invalid configuration."""
        with pytest.raises(
            ValueError, match=r"(?i)overlap must be less than chunk_size",
        ):
            FixedSizeChunker(chunk_size=100, overlap=150)

    def test_metadata_propagation(self):
        """Test metadata is added to chunks."""
        text = "Some text here"
        metadata = {"source": "test"}
        chunker = FixedSizeChunker(chunk_size=10, overlap=0)
        chunks = chunker.chunk(text, metadata=metadata)

        assert all(c.metadata == metadata for c in chunks)


class TestRecursiveChunker:
    """Test recursive chunking."""

    def test_basic_recursive(self, chunking_sample_text):
        """Test basic recursive chunking."""
        chunker = RecursiveChunker(chunk_size=100, overlap=20)
        chunks = chunker.chunk(chunking_sample_text)

        assert len(chunks) > 0
        assert all(isinstance(c, Chunk) for c in chunks)

    def test_paragraph_splitting(self, chunking_sample_text):
        """Test splitting on paragraph boundaries."""
        chunker = RecursiveChunker(
            chunk_size=500,
            overlap=0,
            separators=[r"\n\n", r"\. ", r" "],
        )
        chunks = chunker.chunk(chunking_sample_text)

        # Should split on paragraphs first
        assert len(chunks) > 0
        # First chunk should be roughly a paragraph
        assert "\n\n" not in chunks[0].text or len(chunks) == 1

    def test_custom_separators(self):
        """Test custom separators."""
        text = "Part1|Part2|Part3|Part4"
        chunker = RecursiveChunker(
            chunk_size=10,
            overlap=0,
            separators=[r"\|"],
            is_regex=True,
        )
        chunks = chunker.chunk(text)

        # Should create multiple chunks (may not be exactly 4 due to chunking logic)
        assert len(chunks) >= 2
        # Should respect separator
        assert any("|" in c.text for c in chunks)

    def test_fallback_to_fixed_size(self):
        """Test fallback when no separator found."""
        text = "a" * 1000  # No separators
        chunker = RecursiveChunker(chunk_size=100, overlap=0)
        chunks = chunker.chunk(text)

        # Should fall back to fixed-size chunking
        assert len(chunks) > 0

    def test_empty_text(self):
        """Test empty text."""
        chunker = RecursiveChunker()
        chunks = chunker.chunk("")

        assert len(chunks) == 0

    def test_invalid_config(self):
        """Test invalid configuration."""
        with pytest.raises(
            ValueError, match=r"(?i)overlap must be less than chunk_size",
        ):
            RecursiveChunker(chunk_size=100, overlap=100)
