"""Provider-specific cache annotation strategies for prompt assembly."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from lexigram.contracts.ai.llm import ChatMessage, TokenCounterProtocol
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)

ANTHROPIC_MIN_CACHE_TOKENS = 1024
ANTHROPIC_HAIKU_MIN_CACHE_TOKENS = 2048
ANTHROPIC_MAX_BREAKPOINTS = 4
DEEPSEEK_PADDING_BOUNDARY = 64
GEMINI_CONTEXT_CACHE_MIN_TOKENS = 32_000


@runtime_checkable
class CacheStrategy(Protocol):
    """Protocol for provider-specific cache annotation strategies."""

    def annotate(
        self,
        messages: list[ChatMessage],
        static_count: int,
        token_counter: TokenCounterProtocol | None = None,
    ) -> list[ChatMessage]:
        """Annotate messages with provider-specific cache hints.

        Args:
            messages: Full assembled message list.
            static_count: Number of messages that are static (from beginning).
            token_counter: Optional token counter for size-aware annotations.

        Returns:
            Messages with provider-specific cache annotations applied.
        """
        ...


class PassthroughCacheStrategy:
    """No-op strategy — returns messages unchanged.

    Used for unknown providers or when caching is not applicable.
    """

    def annotate(
        self,
        messages: list[ChatMessage],
        static_count: int,
        token_counter: TokenCounterProtocol | None = None,
    ) -> list[ChatMessage]:
        """Return messages unchanged."""
        return messages


class AnthropicCacheStrategy:
    """Anthropic prompt caching strategy.

    Inserts cache_control: {"type": "ephemeral"} on up to 4 static blocks.
    Minimum 1,024 tokens per cached block (2,048 for Haiku models).
    """

    def __init__(self, min_tokens: int = ANTHROPIC_MIN_CACHE_TOKENS) -> None:
        """Initialize with token minimum threshold.

        Args:
            min_tokens: Minimum tokens required to mark a block as cacheable.
        """
        self._min_tokens = min_tokens

    def annotate(
        self,
        messages: list[ChatMessage],
        static_count: int,
        token_counter: TokenCounterProtocol | None = None,
    ) -> list[ChatMessage]:
        """Insert cache_control on eligible static blocks."""
        result = list(messages)
        breakpoints = 0
        for i in range(min(static_count, len(result))):
            if breakpoints >= ANTHROPIC_MAX_BREAKPOINTS:
                break
            msg = result[i]
            token_count = (
                token_counter.count(str(msg.content or ""))
                if token_counter
                else self._min_tokens
            )
            if token_count >= self._min_tokens:
                # Add cache_control to the message's additional fields
                updated = _set_cache_control(msg, {"type": "ephemeral"})
                result[i] = updated
                breakpoints += 1
                logger.debug(
                    "anthropic_cache_breakpoint_added",
                    index=i,
                    tokens=token_count,
                    breakpoints=breakpoints,
                )
        return result


class OpenAICacheStrategy:
    """OpenAI prompt caching strategy.

    No annotations needed — OpenAI caches automatically when first 1,024+
    tokens are byte-identical. Warns if static prefix is too short.
    """

    def annotate(
        self,
        messages: list[ChatMessage],
        static_count: int,
        token_counter: TokenCounterProtocol | None = None,
    ) -> list[ChatMessage]:
        """Validate prefix length and return messages unchanged."""
        if token_counter and static_count > 0:
            static_messages = messages[:static_count]
            static_tokens = token_counter.count_messages(static_messages)
            if static_tokens < 1024:
                logger.warning(
                    "openai_cache_prefix_too_short",
                    static_tokens=static_tokens,
                    minimum=1024,
                )
        return messages


class DeepSeekCacheStrategy:
    """DeepSeek cache strategy.

    Pads static blocks to the nearest 64-token boundary using neutral
    whitespace. Requires TokenCounterProtocol for accurate padding.
    """

    def annotate(
        self,
        messages: list[ChatMessage],
        static_count: int,
        token_counter: TokenCounterProtocol | None = None,
    ) -> list[ChatMessage]:
        """Pad static messages to 64-token boundaries."""
        if token_counter is None:
            logger.warning("deepseek_cache_no_token_counter", action="skipping_padding")
            return messages
        result = list(messages)
        for i in range(min(static_count, len(result))):
            msg = result[i]
            content = str(msg.content or "")
            current_tokens = token_counter.count(content)
            remainder = current_tokens % DEEPSEEK_PADDING_BOUNDARY
            if remainder != 0:
                # Calculate target token count (next multiple of 64)
                target_tokens = current_tokens + (DEEPSEEK_PADDING_BOUNDARY - remainder)
                # Iteratively add spaces until we reach the target token count
                padded_content = content
                max_iterations = (
                    target_tokens * 10
                )  # Upper bound to prevent infinite loop
                for _ in range(max_iterations):
                    padded_content += " "
                    if token_counter.count(padded_content) >= target_tokens:
                        break
                result[i] = _update_content(msg, padded_content)
                logger.debug(
                    "deepseek_cache_padding_applied",
                    index=i,
                    original_tokens=current_tokens,
                    target_tokens=target_tokens,
                    padded_tokens=token_counter.count(padded_content),
                )
        return result


class GeminiCacheStrategy:
    """Gemini context caching strategy.

    Flags static blocks >32k tokens for Context Caching API pre-creation.
    Below 32k, passes through unchanged.
    """

    def annotate(
        self,
        messages: list[ChatMessage],
        static_count: int,
        token_counter: TokenCounterProtocol | None = None,
    ) -> list[ChatMessage]:
        """Flag large static blocks for context caching."""
        if token_counter and static_count > 0:
            static_messages = messages[:static_count]
            total_tokens = token_counter.count_messages(static_messages)
            if total_tokens > GEMINI_CONTEXT_CACHE_MIN_TOKENS:
                logger.info(
                    "gemini_context_cache_recommended",
                    static_tokens=total_tokens,
                    threshold=GEMINI_CONTEXT_CACHE_MIN_TOKENS,
                )
        return messages


class MistralCacheStrategy:
    """Mistral prefix caching strategy.

    Ensures stable [INST] prefix structure for prefix caching.
    Passes messages through — structure is enforced at assembly time.
    """

    def annotate(
        self,
        messages: list[ChatMessage],
        static_count: int,
        token_counter: TokenCounterProtocol | None = None,
    ) -> list[ChatMessage]:
        """Return messages unchanged — structure enforced in assembler."""
        return messages


def _set_cache_control(msg: ChatMessage, cache_control: dict[str, Any]) -> ChatMessage:
    """Return a new ChatMessage with cache_control added to metadata."""
    from dataclasses import replace as _dc_replace

    try:
        metadata = dict(msg.metadata or {})
        metadata["cache_control"] = cache_control
        return _dc_replace(msg, metadata=metadata)
    except (TypeError, AttributeError) as e:
        logger.warning(
            "cache_control_not_supported",
            reason=f"Failed to set cache_control: {e}",
        )
        return msg


def _update_content(msg: ChatMessage, content: str) -> ChatMessage:
    """Return a new ChatMessage with updated content."""
    from dataclasses import replace as _dc_replace

    return _dc_replace(msg, content=content)


class ProviderCacheStrategyRegistry:
    """Registry mapping provider names to cache annotation strategies.

    Uses registry-based dispatch — no if/elif chains.

    Usage::

        registry = ProviderCacheStrategyRegistry.with_defaults()
        strategy = registry.for_provider("anthropic")
        annotated = strategy.annotate(messages, static_count=3, token_counter=counter)
    """

    def __init__(self) -> None:
        """Create an empty registry."""
        self._strategies: dict[str, CacheStrategy] = {}
        self._default: CacheStrategy = PassthroughCacheStrategy()

    @classmethod
    def _default_entries(cls) -> dict[str, CacheStrategy]:
        """Declare the built-in provider cache strategies."""
        return {
            "anthropic": AnthropicCacheStrategy(),
            "openai": OpenAICacheStrategy(),
            "azure": OpenAICacheStrategy(),
            "deepseek": DeepSeekCacheStrategy(),
            "gemini": GeminiCacheStrategy(),
            "mistral": MistralCacheStrategy(),
            "*": PassthroughCacheStrategy(),
        }

    @classmethod
    def with_defaults(cls) -> ProviderCacheStrategyRegistry:
        """Create a registry pre-populated with all provider strategies."""
        registry = cls()
        for provider, strategy in cls._default_entries().items():
            registry.register(provider, strategy)
        return registry

    def register(self, provider: str, strategy: CacheStrategy) -> None:
        """Register a strategy for a provider key.

        Args:
            provider: Provider name (e.g. "anthropic", "openai").
            strategy: Cache annotation strategy.
        """
        self._strategies[provider] = strategy

    def for_provider(self, provider: str) -> CacheStrategy:
        """Get the strategy for the given provider.

        Falls back to wildcard '*' strategy if provider not found, then to
        PassthroughCacheStrategy default.

        Args:
            provider: Provider name.

        Returns:
            CacheStrategy for the provider (or wildcard/passthrough fallback).
        """
        return (
            self._strategies.get(provider) or self._strategies.get("*") or self._default
        )
