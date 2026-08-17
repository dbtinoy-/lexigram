"""Tests for LLMLingua2 compression strategy."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from lexigram.ai.rag.context_compression.types import (
    CompressionResult,
    CompressionStrategy,
)


@pytest.fixture
def mock_llmlingua() -> MagicMock:
    """Mock the llmlingua module."""
    mock = MagicMock()
    mock_compressor_instance = MagicMock()
    mock_compressor_instance.compress_prompt.return_value = {
        "compressed_prompt": "compressed text"
    }
    mock.PromptCompressor.return_value = mock_compressor_instance
    return mock


@pytest.fixture
def llmlingua2_strategy(mock_llmlingua: MagicMock):
    """Create a LLMLingua2CompressorStrategy with mocked llmlingua."""
    with patch.dict(sys.modules, {"llmlingua": mock_llmlingua}):
        from lexigram.ai.rag.context_compression.strategies.llmlingua2 import (
            LLMLingua2CompressorStrategy,
        )

        return LLMLingua2CompressorStrategy()


@pytest.fixture
def llmlingua2_handler(llmlingua2_strategy):
    """Create a LLMLingua2StrategyHandler."""
    with patch.dict(sys.modules, {"llmlingua": MagicMock()}):
        from lexigram.ai.rag.context_compression.strategies.llmlingua2 import (
            LLMLingua2StrategyHandler,
        )

        return LLMLingua2StrategyHandler(llmlingua2_strategy)


class TestLLMLingua2StrategyHandler:
    """Tests for LLMLingua2StrategyHandler."""

    def test_can_handle_llmlingua2_strategy(self, llmlingua2_handler) -> None:
        """Handler should return True for CompressionStrategy.LLMLINGUA2."""
        assert llmlingua2_handler.can_handle(CompressionStrategy.LLMLINGUA2) is True

    def test_can_handle_other_strategy_returns_false(self, llmlingua2_handler) -> None:
        """Handler should return False for other strategies."""
        assert llmlingua2_handler.can_handle(CompressionStrategy.EXTRACTIVE) is False
        assert llmlingua2_handler.can_handle(CompressionStrategy.ABSTRACTIVE) is False
        assert llmlingua2_handler.can_handle(CompressionStrategy.TOKEN_LIMIT) is False

    @pytest.mark.asyncio
    async def test_create_and_compress_returns_compression_result(
        self, llmlingua2_handler
    ) -> None:
        """Should return a CompressionResult instance."""
        # Use longer text (~200 tokens) to trigger compression (target < current)
        long_text = "a" * 800
        result = await llmlingua2_handler.create_and_compress(
            strategy=CompressionStrategy.LLMLINGUA2,
            context=long_text,
            query="some query",
            kwargs={"target_token_count": 100},
        )

        assert isinstance(result, CompressionResult)
        assert result.strategy == CompressionStrategy.LLMLINGUA2
        assert result.compressed_text == "compressed text"

    @pytest.mark.asyncio
    async def test_create_and_compress_normalizes_list_context(
        self, llmlingua2_handler, mock_llmlingua
    ) -> None:
        """Should normalize list context to string joined by newlines."""
        # Use longer parts to trigger compression (not within budget)
        mock_compressor = mock_llmlingua.PromptCompressor.return_value
        mock_compressor.compress_prompt.return_value = {"compressed_prompt": "compressed"}
        
        result = await llmlingua2_handler.create_and_compress(
            strategy=CompressionStrategy.LLMLINGUA2,
            context=["part1" * 50, "part2" * 50, "part3" * 50],  # Long parts
            query="query",
            kwargs={"target_token_count": 50},  # Target less than current
        )

        assert result.original_text == ("part1" * 50) + "\n\n" + ("part2" * 50) + "\n\n" + ("part3" * 50)

    @pytest.mark.asyncio
    async def test_compress_calculates_rate_correctly(
        self, llmlingua2_strategy
    ) -> None:
        """Should calculate compression rate correctly."""
        text = "a" * 400  # ~100 tokens (400 chars / 4)
        target_tokens = 50

        with patch.object(
            llmlingua2_strategy._compressor, "compress_prompt"
        ) as mock_compress:
            mock_compress.return_value = {"compressed_prompt": "compressed"}

            await llmlingua2_strategy.compress(
                context=text,
                query="test query",
                target_token_count=target_tokens,
            )

            # compression_rate = 50 / 100 = 0.5
            call_args = mock_compress.call_args
            assert call_args[1]["rate"] == 0.5

    @pytest.mark.asyncio
    async def test_compress_rate_clamped_at_floor(
        self, llmlingua2_strategy
    ) -> None:
        """Should clamp compression rate at 0.1 floor."""
        text = "a" * 4000  # ~1000 tokens
        target_tokens = 5

        with patch.object(
            llmlingua2_strategy._compressor, "compress_prompt"
        ) as mock_compress:
            mock_compress.return_value = {"compressed_prompt": "compressed"}

            await llmlingua2_strategy.compress(
                context=text,
                query="test query",
                target_token_count=target_tokens,
            )

            # compression_rate should be 0.1 (floor), not 0.005 (5 / 1000)
            call_args = mock_compress.call_args
            assert call_args[1]["rate"] == 0.1

    @pytest.mark.asyncio
    async def test_compress_rate_clamped_at_ceiling(
        self, llmlingua2_strategy
    ) -> None:
        """Should clamp compression rate at 0.9 ceiling."""
        text = "a" * 4000  # ~1000 tokens
        target_tokens = 950

        with patch.object(
            llmlingua2_strategy._compressor, "compress_prompt"
        ) as mock_compress:
            mock_compress.return_value = {"compressed_prompt": "compressed"}

            await llmlingua2_strategy.compress(
                context=text,
                query="test query",
                target_token_count=target_tokens,
            )

            # compression_rate should be 0.9 (ceiling), not 0.95 (950 / 1000)
            call_args = mock_compress.call_args
            assert call_args[1]["rate"] == 0.9

    @pytest.mark.asyncio
    async def test_compress_skips_when_within_budget(
        self, llmlingua2_strategy
    ) -> None:
        """Should skip compression when context is already within token budget.

        When current_token_estimate <= target_token_count, compress() should
        return unchanged text with compression_ratio=1.0 without calling llmlingua.
        """
        text = "a" * 400  # ~100 tokens
        target_tokens = 200

        with patch.object(
            llmlingua2_strategy._compressor, "compress_prompt"
        ) as mock_compress:
            result = await llmlingua2_strategy.compress(
                context=text,
                query="test query",
                target_token_count=target_tokens,
            )

            # Should NOT call llmlingua at all
            mock_compress.assert_not_called()

            # Result should be unchanged
            assert result.original_text == text
            assert result.compressed_text == text
            assert result.original_tokens == 100
            assert result.compressed_tokens == 100
            assert result.compression_ratio == 1.0
            assert result.strategy == CompressionStrategy.LLMLINGUA2


    @pytest.mark.asyncio
    async def test_force_tokens_merged_with_defaults(self, llmlingua2_strategy) -> None:
        """Should merge custom force_tokens with defaults."""
        text = "a" * 4000  # ~1000 tokens — long enough to require compression
        custom_tokens = ["custom1", "custom2"]

        with patch.object(
            llmlingua2_strategy._compressor, "compress_prompt"
        ) as mock_compress:
            mock_compress.return_value = {"compressed_prompt": "compressed"}

            await llmlingua2_strategy.compress(
                context=text,
                query="test query",
                target_token_count=100,  # Far below current
                force_tokens=custom_tokens,
            )

            call_args = mock_compress.call_args
            force_tokens_arg = call_args[1]["force_tokens"]

            # Custom tokens should be added to default list
            assert "custom1" in force_tokens_arg
            assert "custom2" in force_tokens_arg
            assert "def " in force_tokens_arg  # default token
            assert "class " in force_tokens_arg  # default token

    def test_strategy_not_available_without_llmlingua(self) -> None:
        """_llmlingua_available should return False when import fails."""
        with patch.dict(sys.modules, {"llmlingua": None}):
            # Force reimport to test the check
            import importlib

            from lexigram.ai.rag.context_compression.strategies import llmlingua2

            importlib.reload(llmlingua2)
            assert llmlingua2._llmlingua_available() is False

    @pytest.mark.asyncio
    async def test_create_and_compress_default_target_tokens(
        self, llmlingua2_handler
    ) -> None:
        """Should use default target_token_count of 512 when not specified."""
        result = await llmlingua2_handler.create_and_compress(
            strategy=CompressionStrategy.LLMLINGUA2,
            context="text",
            query="query",
            kwargs={},  # No target_token_count
        )

        # Default is 512, so should process with that
        assert isinstance(result, CompressionResult)

    @pytest.mark.asyncio
    async def test_compression_ratio_calculation(
        self, llmlingua2_handler, mock_llmlingua
    ) -> None:
        """Should calculate compression_ratio correctly."""
        # Modify the mock to return compressed text of different length
        mock_compressor = mock_llmlingua.PromptCompressor.return_value
        mock_compressor.compress_prompt.return_value = {"compressed_prompt": "a" * 200}

        result = await llmlingua2_handler.create_and_compress(
            strategy=CompressionStrategy.LLMLINGUA2,
            context="a" * 400,
            query="query",
            kwargs={"target_token_count": 50},  # Below current to trigger compression
        )

        # Exact calculation: compressed_tokens / original_tokens
        # Original: 400 chars = ~100 tokens, Compressed: 200 chars = ~50 tokens
        expected_ratio = 50 / 100
        assert abs(result.compression_ratio - expected_ratio) < 0.01

    @pytest.mark.asyncio
    async def test_token_savings_calculation(
        self, llmlingua2_handler, mock_llmlingua
    ) -> None:
        """Should calculate token_savings through CompressionResult."""
        # Modify the mock to return compressed text of different length
        mock_compressor = mock_llmlingua.PromptCompressor.return_value
        mock_compressor.compress_prompt.return_value = {"compressed_prompt": "a" * 200}

        result = await llmlingua2_handler.create_and_compress(
            strategy=CompressionStrategy.LLMLINGUA2,
            context="a" * 400,
            query="query",
            kwargs={"target_token_count": 50},  # Below current to trigger compression
        )

        # token_savings = 100 - 50 = 50
        assert result.token_savings == 50


__all__ = []
