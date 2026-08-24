"""Tests for CompressionResult."""

from __future__ import annotations

import pytest

try:
    from lexigram.ai.rag.context_compression import CompressionResult, CompressionStrategy
except ImportError as e:
    pytest.skip(f"context_compression import failed: {e}", allow_module_level=True)


class TestCompressionResult:
    """Tests for CompressionResult."""

    def test_creation(self):
        result = CompressionResult(
            original_text="Original text here",
            compressed_text="Compressed",
            original_tokens=100,
            compressed_tokens=50,
            compression_ratio=0.5,
            strategy=CompressionStrategy.EXTRACTIVE,
        )

        assert result.original_text == "Original text here"
        assert result.compressed_text == "Compressed"
        assert result.original_tokens == 100
        assert result.compressed_tokens == 50
        assert result.compression_ratio == 0.5
        assert result.strategy == CompressionStrategy.EXTRACTIVE

    def test_token_savings(self):
        result = CompressionResult(
            original_text="text",
            compressed_text="txt",
            original_tokens=100,
            compressed_tokens=40,
            compression_ratio=0.4,
            strategy=CompressionStrategy.EXTRACTIVE,
        )

        assert result.token_savings == 60
        assert result.savings_percentage == 60.0

    def test_zero_tokens(self):
        result = CompressionResult(
            original_text="",
            compressed_text="",
            original_tokens=0,
            compressed_tokens=0,
            compression_ratio=1.0,
            strategy=CompressionStrategy.EXTRACTIVE,
        )

        assert result.savings_percentage == 0.0

    def test_repr(self):
        result = CompressionResult(
            original_text="text",
            compressed_text="txt",
            original_tokens=100,
            compressed_tokens=50,
            compression_ratio=0.5,
            strategy=CompressionStrategy.EXTRACTIVE,
        )

        repr_str = repr(result)
        assert "ratio=0.50" in repr_str
        assert "100→50" in repr_str
