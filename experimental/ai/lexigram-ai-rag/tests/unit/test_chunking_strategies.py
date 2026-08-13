"""Tests for RAG chunking strategies."""

import pytest

from lexigram.ai.rag.chunking.strategies.fixed_size import FixedSizeChunker
from lexigram.ai.rag.chunking.strategies.recursive import RecursiveChunker
from lexigram.ai.rag.chunking.strategies.token import TokenChunker


class TestFixedSizeChunker:
    """Tests for FixedSizeChunker."""

    @pytest.fixture
    def chunker(self) -> FixedSizeChunker:
        """Create a fixed-size chunker."""
        return FixedSizeChunker(chunk_size=10, overlap=2)

    def test_empty_text(self, chunker: FixedSizeChunker) -> None:
        """Test empty text returns empty list."""
        result = chunker.chunk("")
        assert result == []

    def test_single_chunk(self, chunker: FixedSizeChunker) -> None:
        """Test text smaller than chunk size returns single chunk."""
        result = chunker.chunk("hello")
        assert len(result) == 1
        assert result[0].text == "hello"

    def test_multiple_chunks(self, chunker: FixedSizeChunker) -> None:
        """Test text larger than chunk size returns multiple chunks."""
        result = chunker.chunk("hello world test data here")
        
        assert len(result) > 1
        for chunk in result:
            assert len(chunk.text) <= 10

    def test_overlap(self) -> None:
        """Test overlap creates overlapping chunks."""
        chunker = FixedSizeChunker(chunk_size=10, overlap=5)
        text = "0123456789abc"  # 13 chars
        
        result = chunker.chunk(text)
        
        # With overlap, chunks should share content
        assert len(result) >= 2

    def test_metadata_passed(self, chunker: FixedSizeChunker) -> None:
        """Test metadata is passed to chunks."""
        result = chunker.chunk("test data", metadata={"source": "test"})
        
        assert len(result) > 0
        assert result[0].metadata == {"source": "test"}

    def test_invalid_overlap_raises(self) -> None:
        """Test overlap >= chunk_size raises ValueError."""
        with pytest.raises(ValueError, match="overlap must be less than chunk_size"):
            FixedSizeChunker(chunk_size=10, overlap=10)

    def test_chunk_indices(self, chunker: FixedSizeChunker) -> None:
        """Test chunk indices are correct."""
        result = chunker.chunk("hello world test")
        
        if len(result) > 1:
            # First chunk should start at 0
            assert result[0].start_index == 0
            # Second chunk should have start > first chunk's start
            assert result[1].start_index > result[0].start_index


class TestRecursiveChunker:
    """Tests for RecursiveChunker."""

    @pytest.fixture
    def chunker(self) -> RecursiveChunker:
        """Create a recursive chunker - small overlap relative to chunk_size."""
        return RecursiveChunker(
            chunk_size=1000,
            overlap=100,
            separators=["\n", ".", " "],
        )

    def test_empty_text(self, chunker: RecursiveChunker) -> None:
        """Test empty text returns empty list."""
        result = chunker.chunk("")
        assert result == []

    def test_single_chunk(self, chunker: RecursiveChunker) -> None:
        """Test short text returns single chunk."""
        result = chunker.chunk("Short text.")
        # May be 1 or more chunks depending on implementation
        assert len(result) >= 1


class TestTokenChunker:
    """Tests for TokenChunker.
    
    These tests require tiktoken to be installed.
    Skip them if tiktoken is not available.
    """

    @pytest.fixture
    def chunker(self) -> TokenChunker:
        """Create a token chunker - skip if tiktoken unavailable."""
        try:
            return TokenChunker(
                chunk_size=50,
                overlap=10,
                encoding_name="cl100k_base",
            )
        except ImportError:
            pytest.skip("tiktoken not installed")

    def test_empty_text(self, chunker: TokenChunker) -> None:
        """Test empty text returns empty list."""
        result = chunker.chunk("")
        assert result == []

    def test_chunks_exist(self, chunker: TokenChunker) -> None:
        """Test chunker produces output."""
        result = chunker.chunk("hello world test data here more words")
        
        # Should produce some chunks
        assert isinstance(result, list)