"""LLM router demo — content generation with ScriptedLLMClient.

Convention followed: **Package exports** — ``__init__.py`` re-exports
the public API surface without defining logic.

Exports:

- ``create_app`` — composition root for the application
- ``ContentGenConfig`` — demo configuration model
- ``ContentGenProvider`` — DI provider for content generation services
"""

from __future__ import annotations

from content_gen.app import create_app
from content_gen.config import ContentGenConfig
from content_gen.di.provider import ContentGenProvider

__all__ = [
    "ContentGenConfig",
    "ContentGenProvider",
    "create_app",
]
