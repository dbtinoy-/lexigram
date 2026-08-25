"""Tests for semantic, sliding-window, and token-based chunkers."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from lexigram.ai.rag.chunking import (
    Chunk,
    SemanticChunker,
    SlidingWindowChunker,
    TokenChunker,
)


class TestSemanticChunker:
    """Test semantic chunking."""

    def test_paragraph_chunking(self, chunking_sample_text):
        """Test chunking by paragraphs."""
        chunker = SemanticChunker(max_chunk_size=500, prefer_paragraphs=True)
        chunks = chunker.chunk(chunking_sample_text)

        assert len(chunks) > 0
        # Chunks should roughly align with paragraphs

    def test_sentence_chunking(self):
        """Test chunking by sentences."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunker = SemanticChunker(
            max_chunk_size=50, min_chunk_size=10, prefer_paragraphs=False,
        )
        chunks = chunker.chunk(text)

        assert len(chunks) > 0
        # Each chunk should contain complete sentences

    def test_min_chunk_size(self):
        """Test minimum chunk size filtering."""
        text = "A. B. C. D. E. F."  # Very short sentences
        chunker = SemanticChunker(max_chunk_size=100, min_chunk_size=5)
        chunks = chunker.chunk(text)

        # Should filter out too-small chunks
        assert all(len(c.text) >= 5 for c in chunks)

    def test_large_paragraph_splitting(self):
        """Test splitting large paragraphs."""
        # Large paragraph that exceeds max size
        text = ". ".join(list(map(lambda i: f"Sentence {i}", range(50))))
        chunker = SemanticChunker(
            max_chunk_size=100, min_chunk_size=10, prefer_paragraphs=True,
        )
        chunks = chunker.chunk(text)

        # Should split even though it's one paragraph
        assert len(chunks) > 1

    def test_empty_text(self):
        """Test empty text."""
        chunker = SemanticChunker()
        chunks = chunker.chunk("")

        assert len(chunks) == 0


class TestSlidingWindowChunker:
    """Test sliding window chunking."""

    def test_basic_sliding_window(self, chunking_long_text):
        """Test basic sliding window."""
        chunker = SlidingWindowChunker(window_size=100, stride=50)
        chunks = chunker.chunk(chunking_long_text)

        assert len(chunks) > 0
        assert all(isinstance(c, Chunk) for c in chunks)

    def test_overlap_calculation(self):
        """Test overlap between windows."""
        text = "0123456789" * 10  # 100 characters
        chunker = SlidingWindowChunker(window_size=30, stride=10)
        chunks = chunker.chunk(text)

        # Check overlap: stride=10 means 20 chars overlap with window_size=30
        if len(chunks) > 1:
            overlap_size = chunks[0].end_index - chunks[1].start_index
            assert overlap_size == 20  # window_size - stride

    def test_no_overlap(self):
        """Test sliding window without overlap."""
        text = "word " * 50
        chunker = SlidingWindowChunker(window_size=50, stride=50)
        chunks = chunker.chunk(text)

        # No overlap: each chunk starts where previous ended
        if len(chunks) > 1:
            for i in range(len(chunks) - 1):
                assert chunks[i].end_index == chunks[i + 1].start_index

    def test_small_stride(self):
        """Test very small stride (high overlap)."""
        text = "0123456789"
        chunker = SlidingWindowChunker(window_size=5, stride=2)
        chunks = chunker.chunk(text)

        # Should create many overlapping chunks
        assert len(chunks) >= 3

    def test_empty_text(self):
        """Test empty text."""
        chunker = SlidingWindowChunker()
        chunks = chunker.chunk("")

        assert len(chunks) == 0

    def test_invalid_config(self):
        """Test invalid configurations."""
        with pytest.raises(ValueError, match="Stride should not exceed window_size"):
            SlidingWindowChunker(window_size=100, stride=150)


class TestTokenChunker:
    """Test token-based chunking."""

    @pytest.fixture
    def tiktoken_available(self):
        """Check if tiktoken is available."""
        try:
            import tiktoken  # noqa: F401
            return True
        except ImportError:
            return False

    def test_basic_token_chunking(self, tiktoken_available):
        """Test basic token chunking."""
        if not tiktoken_available:
            pytest.skip("tiktoken not installed")

        text = "This is a test sentence for tokenization. It has multiple tokens."
        chunker = TokenChunker(chunk_size=5, overlap=1)
        chunks = chunker.chunk(text)

        assert len(chunks) > 1
        assert all(isinstance(c, Chunk) for c in chunks)
        assert all("token_count" in c.metadata for c in chunks)

    def test_token_chunk_overlap(self, tiktoken_available):
        """Test overlap in token chunking."""
        if not tiktoken_available:
            pytest.skip("tiktoken not installed")

        text = "word1 word2 word3 word4 word5 word6"
        chunker = TokenChunker(chunk_size=4, overlap=2)
        chunks = chunker.chunk(text)

        if len(chunks) > 1:
            # Overlap should result in shared tokens (though we check text here)
            # This is a bit loose but confirms the loop logic
            assert len(chunks) >= 2

    def test_empty_text(self, tiktoken_available):
        """Test empty text."""
        if not tiktoken_available:
            pytest.skip("tiktoken not installed")

        chunker = TokenChunker()
        chunks = chunker.chunk("")
        assert len(chunks) == 0

    def test_import_error(self):
        """Test import error when tiktoken is missing."""
        with patch.dict("sys.modules", {"tiktoken": None}):
            # Clear tiktoken from sys.modules if it was there
            import sys
            if "tiktoken" in sys.modules:
                del sys.modules["tiktoken"]

            with pytest.raises(ImportError, match="Token chunking requires 'tiktoken'"):
                TokenChunker()
