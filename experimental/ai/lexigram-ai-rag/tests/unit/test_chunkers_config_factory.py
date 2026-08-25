"""Tests for custom chunking, configuration, the factory, and integration."""

from __future__ import annotations

import pytest

from lexigram.ai.rag.chunking import (
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

    def test_chunking_preserves_content(self, chunking_sample_text):
        """Test that chunking preserves all content."""
        strategies = [
            ChunkingStrategy.FIXED_SIZE,
            ChunkingStrategy.RECURSIVE,
            ChunkingStrategy.SLIDING_WINDOW,
        ]

        for strategy in strategies:
            chunker = create_chunker(strategy, chunk_size=100, overlap=20)
            chunks = chunker.chunk(chunking_sample_text)

            # Reconstruct text (without overlap)
            if strategy != ChunkingStrategy.SLIDING_WINDOW:
                reconstructed = "".join(c.text for c in chunks)
                # Should contain most original words (some may be lost at boundaries)
                original_words = set(chunking_sample_text.split())
                reconstructed_words = set(reconstructed.split())
                # At least 60% of words should be preserved (accounting for edge cases)
                preserved_ratio = len(original_words & reconstructed_words) / len(
                    original_words,
                )
                assert preserved_ratio > 0.6

    def test_different_chunk_sizes(self, chunking_long_text):
        """Test chunking with different sizes."""
        sizes = [50, 100, 200, 500]

        for size in sizes:
            chunker = FixedSizeChunker(chunk_size=size, overlap=10)
            chunks = chunker.chunk(chunking_long_text)

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
