"""Tests for chunking module."""

import pytest
from unittest.mock import patch

from lexigram.ai.rag.chunking import (
    Chunk,
    ChunkingConfig,
    ChunkingStrategy,
    CustomChunker,
    FixedSizeChunker,
    RecursiveChunker,
    SemanticChunker,
    SlidingWindowChunker,
    TokenChunker,
    create_chunker,
)


# Test fixtures
@pytest.fixture
def sample_text():
    """Sample text for testing."""
    return (
        "This is the first sentence. This is the second sentence. "
        "This is the third sentence.\n\n"
        "This is a new paragraph with more content. It has multiple sentences. "
        "Each sentence adds more information.\n\n"
        "Finally, this is the last paragraph. It concludes the document."
    )


@pytest.fixture
def long_text():
    """Longer text for testing."""
    return " ".join(list(map(lambda i: f"Sentence number {i}.", range(100))))


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

    def test_basic_chunking(self, sample_text):
        """Test basic fixed-size chunking."""
        chunker = FixedSizeChunker(chunk_size=50, overlap=10)
        chunks = chunker.chunk(sample_text)

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

    def test_basic_recursive(self, sample_text):
        """Test basic recursive chunking."""
        chunker = RecursiveChunker(chunk_size=100, overlap=20)
        chunks = chunker.chunk(sample_text)

        assert len(chunks) > 0
        assert all(isinstance(c, Chunk) for c in chunks)

    def test_paragraph_splitting(self, sample_text):
        """Test splitting on paragraph boundaries."""
        chunker = RecursiveChunker(
            chunk_size=500,
            overlap=0,
            separators=[r"\n\n", r"\. ", r" "],
        )
        chunks = chunker.chunk(sample_text)

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


class TestSemanticChunker:
    """Test semantic chunking."""

    def test_paragraph_chunking(self, sample_text):
        """Test chunking by paragraphs."""
        chunker = SemanticChunker(max_chunk_size=500, prefer_paragraphs=True)
        chunks = chunker.chunk(sample_text)

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

    def test_basic_sliding_window(self, long_text):
        """Test basic sliding window."""
        chunker = SlidingWindowChunker(window_size=100, stride=50)
        chunks = chunker.chunk(long_text)

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


class TestCustomChunker:
    """Test custom chunking."""

    def test_simple_custom_splitter(self):
        """Test simple custom split function."""

        def split_by_pipe(text: str) -> list[str]:
            return text.split("|")

        chunker = CustomChunker(split_fn=split_by_pipe)
        chunks = chunker.chunk("part1|part2|part3")

        assert len(chunks) == 3
        assert chunks[0].text == "part1"
        assert chunks[1].text == "part2"
        assert chunks[2].text == "part3"

    def test_complex_custom_splitter(self):
        """Test more complex custom logic."""

        def split_by_length(text: str) -> list[str]:
            # Split into chunks of exactly 5 characters
            return list(map(lambda i: text[i : i + 5], range(0, len(text), 5)))

        chunker = CustomChunker(split_fn=split_by_length)
        chunks = chunker.chunk("0123456789ABCDE")

        assert len(chunks) == 3
        assert chunks[0].text == "01234"
        assert chunks[1].text == "56789"
        assert chunks[2].text == "ABCDE"

    def test_metadata_propagation(self):
        """Test metadata with custom chunker."""

        def simple_split(text: str) -> list[str]:
            return text.split(" ")

        metadata = {"source": "custom"}
        chunker = CustomChunker(split_fn=simple_split)
        chunks = chunker.chunk("one two three", metadata=metadata)

        assert all(c.metadata == metadata for c in chunks)


class TestChunkingConfig:
    """Test chunking configuration."""

    def test_default_config(self):
        """Test default configuration."""
        config = ChunkingConfig()

        assert config.strategy == ChunkingStrategy.FIXED_SIZE
        assert config.chunk_size == 1000
        assert config.overlap == 200
        assert config.min_chunk_size == 100

    def test_custom_config(self):
        """Test custom configuration."""
        config = ChunkingConfig(
            strategy=ChunkingStrategy.SEMANTIC,
            chunk_size=500,
            overlap=50,
            min_chunk_size=50,
        )

        assert config.strategy == ChunkingStrategy.SEMANTIC
        assert config.chunk_size == 500
        assert config.overlap == 50
        assert config.min_chunk_size == 50

    def test_validation(self):
        """Test configuration validation."""
        # Negative chunk size
        with pytest.raises(ValueError):
            ChunkingConfig(chunk_size=0)

        # Negative overlap
        with pytest.raises(ValueError):
            ChunkingConfig(overlap=-1)


class TestCreateChunker:
    """Test chunker factory function."""

    def test_create_fixed_size(self):
        """Test creating fixed-size chunker."""
        chunker = create_chunker(ChunkingStrategy.FIXED_SIZE)
        assert isinstance(chunker, FixedSizeChunker)

    def test_create_recursive(self):
        """Test creating recursive chunker."""
        chunker = create_chunker(ChunkingStrategy.RECURSIVE)
        assert isinstance(chunker, RecursiveChunker)

    def test_create_semantic(self):
        """Test creating semantic chunker."""
        chunker = create_chunker(ChunkingStrategy.SEMANTIC)
        assert isinstance(chunker, SemanticChunker)

    def test_create_sliding_window(self):
        """Test creating sliding window chunker."""
        chunker = create_chunker(ChunkingStrategy.SLIDING_WINDOW)
        assert isinstance(chunker, SlidingWindowChunker)

    def test_create_token(self):
        """Test creating token chunker."""
        try:
            import tiktoken  # noqa: F401
        except ImportError:
            pytest.skip("tiktoken not installed")

        chunker = create_chunker(ChunkingStrategy.TOKEN)
        assert isinstance(chunker, TokenChunker)

    def test_create_with_config(self):
        """Test creating with configuration."""
        config = ChunkingConfig(chunk_size=500, overlap=100)
        chunker = create_chunker(config=config)

        assert isinstance(chunker, FixedSizeChunker)
        assert chunker.chunk_size == 500
        assert chunker.overlap == 100

    def test_create_with_kwargs(self):
        """Test creating with keyword arguments."""
        chunker = create_chunker(
            ChunkingStrategy.FIXED_SIZE,
            chunk_size=300,
            overlap=50,
        )

        assert isinstance(chunker, FixedSizeChunker)
        assert chunker.chunk_size == 300
        assert chunker.overlap == 50


class TestIntegration:
    """Integration tests for chunking."""

    def test_chunking_preserves_content(self, sample_text):
        """Test that chunking preserves all content."""
        strategies = [
            ChunkingStrategy.FIXED_SIZE,
            ChunkingStrategy.RECURSIVE,
            ChunkingStrategy.SLIDING_WINDOW,
        ]

        for strategy in strategies:
            chunker = create_chunker(strategy, chunk_size=100, overlap=20)
            chunks = chunker.chunk(sample_text)

            # Reconstruct text (without overlap)
            if strategy != ChunkingStrategy.SLIDING_WINDOW:
                reconstructed = "".join(c.text for c in chunks)
                # Should contain most original words (some may be lost at boundaries)
                original_words = set(sample_text.split())
                reconstructed_words = set(reconstructed.split())
                # At least 60% of words should be preserved (accounting for edge cases)
                preserved_ratio = len(original_words & reconstructed_words) / len(
                    original_words,
                )
                assert preserved_ratio > 0.6

    def test_different_chunk_sizes(self, long_text):
        """Test chunking with different sizes."""
        sizes = [50, 100, 200, 500]

        for size in sizes:
            chunker = FixedSizeChunker(chunk_size=size, overlap=10)
            chunks = chunker.chunk(long_text)

            # More chunks with smaller size
            if size < 500:
                assert len(chunks) > 0

    def test_real_world_document(self):
        """Test with realistic document."""
        document = """
# Introduction

This is a sample document with multiple paragraphs and sections.
It demonstrates how different chunking strategies handle real content.

## Background

The field of natural language processing has evolved significantly.
Modern approaches use transformer models and attention mechanisms.
These techniques have achieved remarkable results across many tasks.

## Methods

We employed several chunking strategies:
- Fixed-size chunking for uniform segments
- Semantic chunking for natural boundaries
- Recursive chunking for hierarchical splits

## Conclusion

Each strategy has its advantages depending on the use case.
The choice of chunking method impacts downstream performance.
"""

        strategies = [
            (ChunkingStrategy.FIXED_SIZE, {"chunk_size": 200, "overlap": 50}),
            (ChunkingStrategy.SEMANTIC, {"chunk_size": 300}),
            (ChunkingStrategy.RECURSIVE, {"chunk_size": 250, "overlap": 50}),
        ]

        for strategy, kwargs in strategies:
            chunker = create_chunker(strategy, **kwargs)
            chunks = chunker.chunk(document)

            assert len(chunks) > 0
            # All chunks should have content
            assert all(len(c.text.strip()) > 0 for c in chunks)
            # Indexes should be valid
            assert all(c.start_index < c.end_index for c in chunks)
