"""AI component factory functions for the Lexigram AI provider.

Each factory creates a concrete AI sub-service from its configuration object.
They are extracted from :class:`~lexigram.ai.di.provider.AIProvider` so that
``provider.py`` remains focused on lifecycle management.
"""

from __future__ import annotations

__all__: list[str] = []
