"""Length optimizer for context.

This module implements length optimization to fit context within token limits
while preserving the most relevant information.
"""

from __future__ import annotations

from lexigram.ai.rag.synthesis.types import ContextChunk


class LengthOptimizer:
    """Optimize context length to fit within limits.

    This component truncates or summarizes context to fit within token
    limits while prioritizing the most relevant content.

    Attributes:
        max_tokens: Maximum total tokens allowed
        chars_per_token: Approximate characters per token
        preserve_order: Whether to preserve chunk order
    """

    def __init__(
        self,
        max_tokens: int = 4000,
        chars_per_token: int = 4,
        preserve_order: bool = True,
    ):
        """Initialize the length optimizer.

        Args:
            max_tokens: Maximum tokens allowed
            chars_per_token: Approximate characters per token
            preserve_order: Whether to preserve order
        """
        self.max_tokens = max_tokens
        self.chars_per_token = chars_per_token
        self.preserve_order = preserve_order

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text.

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        return len(text) // self.chars_per_token

    async def optimize_length(
        self,
        chunks: list[ContextChunk],
    ) -> list[ContextChunk]:
        """Optimize chunk list to fit within token limit.

        Args:
            chunks: Chunks to optimize

        Returns:
            Optimized list of chunks
        """
        if not chunks:
            return []

        # Calculate total tokens
        total_tokens = sum(self._estimate_tokens(c.text) for c in chunks)

        # If already within limit, return as-is
        if total_tokens <= self.max_tokens:
            return chunks

        # Sort by score/rank to prioritize best chunks
        sorted_chunks = sorted(
            chunks,
            key=lambda c: (c.score if c.score else 0, -c.rank),
            reverse=True,
        )

        # Greedily select chunks until limit
        selected_chunks: list[ContextChunk] = []
        current_tokens = 0

        for chunk in sorted_chunks:
            chunk_tokens = self._estimate_tokens(chunk.text)

            if current_tokens + chunk_tokens <= self.max_tokens:
                selected_chunks.append(chunk)
                current_tokens += chunk_tokens
            elif current_tokens < self.max_tokens:
                # Try to fit partial chunk
                remaining_tokens = self.max_tokens - current_tokens
                remaining_chars = remaining_tokens * self.chars_per_token

                if remaining_chars >= 100:  # Minimum useful chunk
                    # Truncate chunk
                    truncated_text = chunk.text[:remaining_chars] + "..."
                    truncated_chunk = ContextChunk(
                        text=truncated_text,
                        source=chunk.source,
                        score=chunk.score,
                        metadata={**chunk.metadata, "truncated": True},
                        rank=chunk.rank,
                    )
                    selected_chunks.append(truncated_chunk)
                    break

        # Restore original order if requested
        if self.preserve_order:
            selected_chunks.sort(key=lambda c: c.rank)

        return selected_chunks

    async def optimize_with_budget(
        self,
        chunks: list[ContextChunk],
        token_budget: int,
    ) -> list[ContextChunk]:
        """Optimize chunks with a specific token budget.

        Args:
            chunks: Chunks to optimize
            token_budget: Token budget for this optimization

        Returns:
            Optimized chunks
        """
        original_max = self.max_tokens
        self.max_tokens = token_budget

        result = await self.optimize_length(chunks)

        self.max_tokens = original_max
        return result
