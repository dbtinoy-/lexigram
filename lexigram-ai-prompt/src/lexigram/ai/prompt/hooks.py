"""Root hook payload surface for lexigram-ai-prompt."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "PromptInputSanitizedHook",
    "PromptRenderedHook",
    "PromptTemplateResolvedHook",
]


@dataclass(frozen=True, kw_only=True)
class PromptTemplateResolvedHook:
    """Payload fired when a named prompt template is resolved from the registry."""

    template_name: str


@dataclass(frozen=True, kw_only=True)
class PromptRenderedHook:
    """Payload fired after prompt rendering produces a formatted payload."""

    render_format: str


@dataclass(frozen=True, kw_only=True)
class PromptInputSanitizedHook:
    """Payload fired after prompt input sanitization completes."""
