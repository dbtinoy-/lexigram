"""Integration layer for the app package.

Exports the :class:`CoreProvider` DI provider that bootstraps all
Lexigram framework sub-providers.
"""

from __future__ import annotations

from lexigram.app.di.provider import CoreProvider

__all__ = ["CoreProvider"]
