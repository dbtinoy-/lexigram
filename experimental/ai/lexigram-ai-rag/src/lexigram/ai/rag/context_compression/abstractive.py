"""Abstractive compression strategies."""

from __future__ import annotations

from datetime import UTC, datetime

from lexigram.ai.rag.context_compression.base import AbstractCompressor
from lexigram.ai.rag.context_compression.types import (
    CompressionResult,
    CompressionStrategy,
)
from lexigram.contracts import (
    ChatMessage,
    LLMClientProtocol,
)


class AbstractiveCompressor(AbstractCompressor):
    """LLM-based abstractive compression.

    Uses an LLM to generate a compressed summary that preserves
    the most important information relevant to the query.

    Example:
        >>> compressor = AbstractiveCompressor(
        ...     llm_client=llm,
        ...     max_tokens=150,
        ...     temperature=0.3
        ... )
        >>> result = await compressor.compress(
        ...     context=long_article,
        ...     query="What are the main findings?"
        ... )
    """

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        max_tokens: int = 200,
        temperature: float = 0.3,
    ):
        """Initialize abstractive compressor.

        Args:
            llm_client: LLM client for summarization.
            max_tokens: Maximum tokens for compressed output.
            temperature: Temperature for generation.
        """
        self.llm_client = llm_client
        self.max_tokens = max_tokens
        self.temperature = temperature

    async def compress(
        self,
        context: str | list[str],
        query: str | None = None,
        **kwargs,
    ) -> CompressionResult:
        """Compress using LLM-based summarization."""
        original_text = self._normalize_context(context)
        original_tokens = self._estimate_tokens(original_text)

        # Build summarization prompt
        prompt = self._build_prompt(original_text, query)

        # Generate summary
        result = await self.llm_client.complete(
            messages=[
                ChatMessage(
                    role="system",
                    content="You are a helpful assistant that creates concise, information-dense summaries.",
                ),
                ChatMessage(
                    role="user",
                    content=prompt,
                ),
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        if result.is_err():
            raise result.unwrap_err()
        response = result.unwrap()

        # Extract compressed text
        if hasattr(response, "content"):
            compressed_text = response.content
        elif hasattr(response, "choices") and response.choices:
            compressed_text = response.choices[0].message.content
        elif isinstance(response, dict) and "content" in response:
            compressed_text = response["content"]
        else:
            compressed_text = str(response)

        compressed_tokens = self._estimate_tokens(compressed_text)
        compression_ratio = (
            compressed_tokens / original_tokens if original_tokens > 0 else 1.0
        )

        return CompressionResult(
            original_text=original_text,
            compressed_text=compressed_text,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compression_ratio,
            strategy=CompressionStrategy.ABSTRACTIVE,
            metadata={
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "query_used": query is not None,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    def _build_prompt(self, text: str, query: str | None) -> str:
        """Build summarization prompt."""
        prompt = f"Text to compress:\n\n{text}\n\n"

        if query:
            prompt += f"Focus on information relevant to: {query}\n\n"

        prompt += (
            f"Provide a concise summary in no more than {self.max_tokens // 4} words "
            f"that preserves the most important information"
        )

        if query:
            prompt += " relevant to the query"

        prompt += ":"

        return prompt
