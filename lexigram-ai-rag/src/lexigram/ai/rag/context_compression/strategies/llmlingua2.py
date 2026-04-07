"""LLMLingua-2 prompt compression strategy using XLM-RoBERTa token classification."""

from __future__ import annotations

import asyncio
import importlib.util
from typing import Any

from lexigram.ai.rag.context_compression.types import (
    CompressionResult,
    CompressionStrategy,
)
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


def _llmlingua_available() -> bool:
    """Check if llmlingua package is installed."""
    return importlib.util.find_spec("llmlingua") is not None


class LLMLingua2CompressorStrategy:
    """LLMLingua-2 prompt compression using XLM-RoBERTa token classification.

    Preserves original tokens (extraction, not generation) — no hallucinated
    content. 95%+ QA accuracy retention at 2x compression ratio.

    Raises ImportError at instantiation if llmlingua is not installed.
    """

    def __init__(
        self,
        model_name: str = "microsoft/llmlingua-2-xlm-roberta-large-meetingbank",
        default_force_tokens: list[str] | None = None,
    ) -> None:
        """Initialize the LLMLingua-2 compressor.

        Args:
            model_name: HuggingFace model name for LLMLingua-2.
            default_force_tokens: Tokens that must always be preserved.

        Raises:
            ImportError: If llmlingua package is not installed.
        """
        from llmlingua import PromptCompressor  # type: ignore[import-not-found]

        self._compressor = PromptCompressor(
            model_name=model_name,
            use_llmlingua2=True,
        )
        self._default_force_tokens = default_force_tokens or [
            "```",
            "def ",
            "class ",
            "return ",
            "import ",
            "User:",
            "Assistant:",
            "[INST]",
            "</s>",
        ]

    async def compress(
        self,
        context: list[str] | str,
        query: str,
        target_token_count: int,
        **kwargs: Any,
    ) -> CompressionResult:
        """Compress context to fit within target_token_count.

        Calculates compression rate from current vs target token count,
        then applies LLMLingua-2 binary token classification.

        Args:
            context: The text to compress (str or list[str]).
            query: Query for relevance context (unused by LLMLingua-2).
            target_token_count: Target token count after compression.
            **kwargs: Additional arguments. Supports 'force_tokens' (list[str] | None).

        Returns:
            CompressionResult with compressed text and statistics.
        """
        # Normalize context to string
        if isinstance(context, list):
            text = "\n\n".join(str(c) for c in context)
        else:
            text = str(context)

        # Estimate current token count (~4 chars per token)
        current_token_estimate = max(len(text) // 4, 1)

        # Already within budget — return unchanged
        if current_token_estimate <= target_token_count:
            return CompressionResult(
                original_text=text,
                compressed_text=text,
                original_tokens=current_token_estimate,
                compressed_tokens=current_token_estimate,
                compression_ratio=1.0,
                strategy=CompressionStrategy.LLMLINGUA2,
            )

        compression_rate = max(
            0.1, min(0.9, target_token_count / current_token_estimate)
        )

        force_tokens = kwargs.get("force_tokens")
        all_force_tokens = list(self._default_force_tokens)
        if force_tokens:
            all_force_tokens.extend(force_tokens)

        # LLMLingua's compress_prompt is synchronous — run in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._compressor.compress_prompt(
                text,
                rate=compression_rate,
                force_tokens=all_force_tokens,
            ),
        )
        compressed_text = result["compressed_prompt"]
        compressed_token_estimate = max(len(compressed_text) // 4, 1)

        return CompressionResult(
            original_text=text,
            compressed_text=compressed_text,
            original_tokens=current_token_estimate,
            compressed_tokens=compressed_token_estimate,
            compression_ratio=compressed_token_estimate / current_token_estimate,
            strategy=CompressionStrategy.LLMLINGUA2,
        )


class LLMLingua2StrategyHandler:
    """CompressionStrategyHandler wrapper for LLMLingua2CompressorStrategy.

    Adapts LLMLingua2CompressorStrategy to the CompressionStrategyHandler
    protocol used by CompressionStrategyRegistry.
    """

    def __init__(self, strategy: LLMLingua2CompressorStrategy) -> None:
        """Initialize with the underlying strategy.

        Args:
            strategy: The LLMLingua2CompressorStrategy instance to wrap.
        """
        self._strategy = strategy

    def can_handle(self, strategy: Any) -> bool:
        """Return True for CompressionStrategy.LLMLINGUA2.

        Args:
            strategy: Strategy identifier to check.

        Returns:
            True if strategy is CompressionStrategy.LLMLINGUA2.
        """
        return strategy == CompressionStrategy.LLMLINGUA2

    async def create_and_compress(
        self,
        strategy: Any,
        context: Any,
        query: Any,
        kwargs: dict[str, Any],
    ) -> CompressionResult:
        """Compress context using LLMLingua-2.

        Args:
            strategy: The compression strategy (must be LLMLINGUA2).
            context: Text to compress (str or list[str]).
            query: Query for relevance context (unused by LLMLingua-2).
            kwargs: Additional kwargs. Supports 'target_token_count' (int,
                default 512) and 'force_tokens' (list[str] | None).

        Returns:
            CompressionResult with compressed text and stats.
        """
        target_token_count = int(kwargs.get("target_token_count", 512))
        force_tokens = kwargs.get("force_tokens")

        return await self._strategy.compress(
            context=context,
            query=query,
            target_token_count=target_token_count,
            force_tokens=force_tokens,
        )


__all__ = [
    "LLMLingua2CompressorStrategy",
    "LLMLingua2StrategyHandler",
    "_llmlingua_available",
]
