"""Nil-safe adapter over the optional host conversion context.

The engine is synchronous and side-effect free.  Host capabilities flow
in through :class:`lexigram.contracts.ai.relay.context.RelayConversionContext`
(or ``None``).  This module wraps that context so mappers never guard
against ``None`` callbacks and never touch protocol-specific options
directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lexigram.contracts.ai.relay.context import (
    DefaultMaxTokensCallback,
    MediaResolverProtocol,
    PreserveThinkingSuffixCallback,
    RelayConversionContext,
    RelayOptions,
    SafetySettingCallback,
    SupportsImageGenerationCallback,
)
from lexigram.contracts.ai.relay.types import RelayLoss

__all__ = ["ConversionContext"]


def _no_default_max_tokens(model: str) -> int | None:
    """Nil-safe callback: no default ``max_tokens`` exists."""
    return None


def _no_safety_setting(category: str) -> str | None:
    """Nil-safe callback: no safety threshold is configured."""
    return None


def _no_image_generation(model: str) -> bool:
    """Nil-safe callback: image generation is unsupported."""
    return False


def _no_thinking_suffix(model: str) -> bool:
    """Nil-safe callback: the thinking-suffix bypass policy is off."""
    return False


@dataclass(frozen=True)
class ConversionContext:
    """Per-conversion context with nil-safe callbacks and a loss sink.

    Attributes:
        options: Cross-protocol adaptation options.  Zero-value when the
            host supplied no context.
        default_max_tokens: Claude ``max_tokens`` fallback lookup, always
            callable.
        safety_setting: Gemini safety threshold lookup, always callable.
        supports_image_generation: Gemini image-generation capability
            lookup, always callable.
        preserve_thinking_suffix: Thinking-suffix bypass policy lookup,
            always callable.
        media_resolver: Resolver for URL media, or ``None``.
        losses: Semantic losses recorded during conversion.
    """

    options: RelayOptions = field(default_factory=RelayOptions)
    default_max_tokens: DefaultMaxTokensCallback = _no_default_max_tokens
    safety_setting: SafetySettingCallback = _no_safety_setting
    supports_image_generation: SupportsImageGenerationCallback = _no_image_generation
    preserve_thinking_suffix: PreserveThinkingSuffixCallback = _no_thinking_suffix
    media_resolver: MediaResolverProtocol | None = None
    losses: list[RelayLoss] = field(default_factory=list)

    @classmethod
    def wrap(cls, context: RelayConversionContext | None) -> ConversionContext:
        """Adapt a host context, substituting nil-safe defaults.

        Args:
            context: Host context, or ``None`` when the gateway supplied
                none.

        Returns:
            An adapter with callable callbacks and the host's loss list.
        """
        if context is None:
            return cls()
        return cls(
            options=context.options,
            default_max_tokens=context.default_max_tokens or _no_default_max_tokens,
            safety_setting=context.safety_setting or _no_safety_setting,
            supports_image_generation=context.supports_image_generation
            or _no_image_generation,
            preserve_thinking_suffix=context.preserve_thinking_suffix
            or _no_thinking_suffix,
            media_resolver=context.media_resolver,
            losses=context.losses,
        )

    def max_tokens_for(self, model: str) -> int | None:
        """Return the default ``max_tokens`` for *model*.

        Negative callback results are treated as invalid and yield
        ``None``; mappers apply their own missing-option policy.

        Args:
            model: The already-selected upstream model name.

        Returns:
            A non-negative default, or ``None`` when absent or invalid.
        """
        value = self.default_max_tokens(model)
        if value is None or value < 0:
            return None
        return value

    @staticmethod
    def normalize_model(model: str) -> str:
        """Normalize a model name without selecting a different model.

        Args:
            model: Raw model name from the source payload.

        Returns:
            The cleaned model name.
        """
        return model.strip()
